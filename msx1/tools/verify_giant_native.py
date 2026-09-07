"""Native 32 KiB MSX1 giant-boss checks and captures through localhost:18801.

This is a collection of explicitly seeded boundary scenarios, not a manual
playthrough. The ROM executes all input, collision, PCG upload and page flips.
Readbacks and screenshots are taken with the CPU stopped at named ROM frame
boundaries. Importing this module never connects to an emulator.
"""
from pathlib import Path
import hashlib
import json
import re
import time
import urllib.request

import numpy as np
from PIL import Image

from pcg_codec import decode_screen
from ram32_test_config import ROOT, RELEASE, OUT, STANDARD, MACHINE, VDP, TIMING_SETUP


PLAY, BOSS, TRANSIT, OVER, CLEAR, PAUSED = 1, 2, 3, 4, 5, 6
STATE_PNGS = ('giant-closed.png', 'giant-left-destroyed.png',
              'giant-right-destroyed.png', 'giant-core-open.png')


class NativeBoss:
    def __init__(self):
        self.symbols = json.loads((ROOT/'work/build/symbols.json').read_text())
        self.manifest = json.loads((RELEASE/'build-manifest.json').read_text())
        self.results = []
        self.bp = None
        self.emulator = None
        self.scratch = ROOT/'work'/('captures-giant-v1.3-'+STANDARD)
        self.scratch.mkdir(parents=True, exist_ok=True)
        self.frames = [np.load(ROOT/'assets'/f'boss-frames-{state}.npy') for state in range(4)]
        self.motion = json.loads((RELEASE/'giant-motion.json').read_text())
        source = (ROOT/'src/game.c').read_text()
        match = re.search(r'video_rows\[256\]\s*=\s*\{([^}]+)\}', source)
        assert match, 'Native video-coordinate table not found'
        self.video_rows = [int(value) for value in match[1].split(',')]
        assert len(self.video_rows) == 256
        self.captures = []
        self.fps = None

    @staticmethod
    def cmd(text):
        request = urllib.request.Request('http://127.0.0.1:18801', data=text.encode(), method='POST')
        return urllib.request.urlopen(request, timeout=25).read().decode().strip()

    def read(self, name, size=1):
        address = self.symbols[name]
        terms = [f'{256**i}*[debug read memory {address+i}]' for i in range(size)]
        return int(self.cmd('expr {'+'+'.join(terms)+'}'))

    def put(self, name, value, size=1):
        self.put_many([(name, value, size)])

    def put_many(self, entries):
        self.cmd(';'.join(f'debug write memory {self.symbols[name]+i} {(value>>(8*i))&255}'
                          for name, value, size in entries for i in range(size)))

    def block(self, device, address, size):
        return bytes.fromhex(self.cmd(f'binary encode hex [debug read_block {{{device}}} {address} {size}]'))

    def snapshot(self, fields):
        return {name: self.read(name, size) for name, size in fields}

    def clock(self):
        return float(self.cmd('machine_info time'))

    @staticmethod
    def until(test, label, timeout=60):
        deadline = time.monotonic()+timeout
        while not test():
            if time.monotonic() >= deadline:
                raise AssertionError('60-second emulator guard: '+label)
            time.sleep(.008)

    def check(self, name, passed, **evidence):
        item = dict(name=name, passed=bool(passed), **evidence)
        self.results.append(item)
        print(name, 'PASS' if passed else 'FAIL', evidence, flush=True)
        if not passed:
            raise AssertionError(name)

    def key(self, row, mask, pressed):
        self.cmd(f'keymatrix{"down" if pressed else "up"} {row} {mask}')

    def release_keys(self):
        self.cmd('keymatrixup 8 241;keymatrixup 7 4;keymatrixup 5 32')

    def remove_bp(self):
        if self.bp is not None:
            self.cmd('debug remove_bp '+self.bp)
            self.bp = None

    def stop_at(self, name='_draw_frame', condition='', resume=True):
        self.remove_bp()
        self.bp = self.cmd(f'debug set_bp {self.symbols[name]} {{{condition}}} {{debug break}}')
        if resume:
            self.cmd('if {[debug breaked]} {debug cont}')
        self.until(lambda: self.cmd('debug breaked') == '1', 'breakpoint '+name)

    def frame(self):
        assert self.bp is not None
        self.cmd('debug cont')
        self.until(lambda: self.cmd('debug breaked') == '1', 'next ROM frame boundary')

    def wait_frames(self, predicate, label, maximum=180):
        for _ in range(maximum):
            if predicate():
                return
            self.frame()
        raise AssertionError('Bounded frame wait: '+label)

    def clear_entities(self):
        writes = []
        for name, stride, count in [('_foes', 12, 6), ('_shots', 9, 8), ('_fx', 7, 4)]:
            writes += [f'debug write memory {self.symbols[name]+i*stride} 0' for i in range(count)]
        writes.append(f'debug write memory {self.symbols["_pickup_on"]} 0')
        self.cmd(';'.join(writes))

    def capture(self, path):
        self.cmd(f'openmsx::internal_screenshot -raw -size 640 {{{path.as_posix()}}}')
        return Image.open(path).convert('RGB')

    def visible(self):
        native = self.block('VRAM', 0, 16384)
        base = int(self.cmd('debug read {VDP regs} 2'))*1024
        state = self.read('_world_boss_display_state')
        phase = self.read('_world_phase')
        assert state in range(4) and phase in range(16)
        assert np.array_equal(decode_screen(native, base)[16:176], self.frames[state][phase, 16:176]), f'Native pixels differ: state {state}, phase {phase}'
        assert native[0x1800:0x2000] == (ROOT/'assets/sprite-patterns.bin').read_bytes()
        assert native[0x3800:0x3840] == native[0x3C00:0x3C40]
        assert native[0x3AC0:0x3B00] == native[0x3EC0:0x3F00]
        return state, phase, self.read('_world_pending')

    def hold_damage_state(self, state):
        left, right = (0 if state & 1 else 32), (0 if state & 2 else 32)
        self.put_many([('_mode', BOSS, 1), ('_stage', 4, 1),
                       ('_giant_phase', 3 if state == 3 else 1, 1),
                       ('_giant_left_hp', left, 1), ('_giant_right_hp', right, 1),
                       ('_giant_core_hp', 116, 1), ('_boss_hp', left+right+116, 2),
                       ('_world_boss_state', state, 1), ('_boss_flash', 0, 1),
                       ('_giant_hit_part', 0, 1), ('_stage_banner', 0, 1),
                       ('_bomb_flash', 0, 1), ('_shield', 6, 1),
                       ('_old_keys', 0, 1), ('_keys', 0, 1)])
        self.clear_entities()
        self.wait_frames(lambda: self.read('_world_boss_display_state') == state and self.read('_world_pending') == 0,
                         'damage state becomes visible', maximum=8)

    def entry(self):
        """Only the stage clock is shortened; warning and scene entry run natively."""
        self.release_keys()
        self.put_many([('_mode', PLAY, 1), ('_stage', 4, 1), ('_stage_clock', 1198, 2),
                       ('_world_loaded', 255, 1), ('_giant_phase', 0, 1),
                       ('_giant_left_hp', 0, 1), ('_giant_right_hp', 0, 1),
                       ('_giant_core_hp', 0, 1), ('_giant_gate_clock', 0, 1),
                       ('_world_boss_state', 0, 1), ('_shield', 6, 1), ('_bombs', 3, 1),
                       ('_hurt_clock', 0, 1), ('_bomb_flash', 0, 1), ('_boss_flash', 0, 1),
                       ('_shot_clock', 0, 1), ('_old_keys', 0, 1), ('_keys', 0, 1),
                       ('_transition_clock', 0, 1), ('_player_x', 128, 2),
                       ('_player_y', 166, 2), ('_aim_x', 128, 2), ('_aim_y', 119, 2)])
        self.clear_entities()
        self.wait_frames(lambda: self.read('_mode') == BOSS, 'final stage reaches boss', maximum=4)
        self.check('final-stage-real-boss-entry', self.read('_stage_clock', 2) == 1200 and self.read('_giant_phase') == 0 and self.read('_boss_clock', 2) == 0,
                   seeded_stage_clock=1198, final_stage_clock=self.read('_stage_clock', 2))
        self.check('giant-initial-health', self.read('_giant_left_hp') == 32 and self.read('_giant_right_hp') == 32 and self.read('_giant_core_hp') == 116 and self.read('_boss_hp', 2) == 180)
        for tick in range(1, 36):
            self.frame()
            assert self.read('_giant_phase') == 0 and self.read('_boss_clock', 2) == tick
        self.frame()
        self.check('giant-warning-lasts-36-native-ticks', self.read('_giant_phase') == 1 and self.read('_boss_clock', 2) == 36)
        self.wait_frames(lambda: self.read('_world_loaded') == 5, 'giant PCG scene load', maximum=3)
        self.check('giant-scene-loaded-by-ROM', self.read('_world_loaded') == 5 and self.read('_mode') == BOSS)
        self.visible()

    @staticmethod
    def save_gif(images, times, destination):
        durations, accumulated = [], 0
        for index in range(len(images)):
            end = times[index+1] if index+1 < len(times) else times[index]+times[-1]-times[-2]
            rounded = round((end-times[0])*100)
            durations.append(max(10, (rounded-accumulated)*10))
            accumulated = rounded
        images[0].save(destination, save_all=True, append_images=images[1:], duration=durations, loop=0)

    def all_visual_states(self):
        total = 0
        movement = set()
        damage_images = []
        for state in range(4):
            self.hold_damage_state(state)
            phases, parts, images, stamps = set(), set(), [], []
            for index in range(32):
                displayed, phase, pending = self.visible()
                assert displayed == state
                phases.add(phase); parts.add(pending); total += 1
                target = self.motion[phase]['core']
                assert self.read('_boss_x', 2) == target[0]
                assert self.read('_boss_y', 2) == target[1]*9//8
                movement.add((self.read('_boss_x', 2), self.read('_boss_y', 2)))
                picture = self.capture(self.scratch/f'state-{state}-{index:02}.png')
                images.append(picture); stamps.append(self.clock())
                if index % 4 == 0:
                    damage_images.append(picture)
                self.clear_entities()
                self.frame()
            self.check(f'giant-state-{state}-all-native-PCG-phases', phases == set(range(16)) and parts == {0, 1},
                       raw_VRAM_readbacks=32, phases=sorted(phases), transfer_states=sorted(parts), pixels_per_readback=40960)
            images[0].save(OUT/STATE_PNGS[state])
            self.captures.append(STATE_PNGS[state])
            if state == 0:
                self.save_gif(images, stamps, OUT/'giant-native.gif')
                self.captures.append('giant-native.gif')
                self.check('giant-native-GIF-moves', len({image.tobytes() for image in images}) >= 16,
                           captured_frames=32, unique_frames=len({image.tobytes() for image in images}))
        damage_images[0].save(OUT/'giant-damage-states-native.gif', save_all=True,
                              append_images=damage_images[1:], duration=160, loop=0)
        self.captures.append('giant-damage-states-native.gif')
        self.check('giant-all-states-native-VRAM-readback', total == 128, states=4, phases_per_state=16, readbacks=total)
        self.check('giant-native-motion-anchors-follow-hull', len(movement) >= 4, anchors=sorted(movement))

    def mid_transfer_state_changes(self):
        self.hold_damage_state(0)
        # Enter part A requesting one state, replace that request before B.
        for requested_a, requested_b in ((1, 2), (2, 3), (3, 0)):
            self.wait_frames(lambda: self.read('_world_pending') == 0, 'part A boundary', maximum=3)
            previous = self.visible()[:2]
            self.put('_world_boss_state', requested_a)
            self.frame()
            assert self.read('_world_pending') == 1
            assert self.visible()[:2] == previous
            self.put('_world_boss_state', requested_b)
            self.frame()
            assert self.read('_world_pending') == 0
            assert self.visible()[0] == requested_b
        self.check('giant-state-switch-between-parts-A-and-B', True, native_transitions=3)
        # Stop inside draw_frame after B copied its names but before R2 flips.
        # A new request must not relabel the already prepared name page.
        self.put('_world_boss_state', 1)
        self.frame()
        assert self.read('_world_pending') == 1
        previous = self.visible()[:2]
        address = self.symbols['_world_pending']
        self.stop_at('_world_commit', f'[debug read memory {address}]==2')
        assert self.read('_world_pending') == 2
        assert self.visible()[:2] == previous
        self.put('_world_boss_state', 2)
        self.stop_at('_draw_frame')
        self.check('giant-state-is-latched-before-name-page-flip', self.read('_world_boss_display_state') == 1 and self.read('_world_boss_state') == 2)
        self.visible()

    def pauses(self):
        fields = [(name, 1) for name in ('_stage', '_giant_phase', '_giant_left_hp', '_giant_right_hp',
                  '_giant_core_hp', '_giant_gate_clock', '_giant_hit_part', '_world_loaded', '_world_phase',
                  '_world_page', '_world_pending', '_world_target', '_world_boss_state', '_world_boss_display_state',
                  '_shot_clock', '_hurt_clock', '_bomb_flash', '_boss_flash', '_shield', '_bombs')]
        fields += [(name, 2) for name in ('_boss_clock', '_boss_hp', '_frame_counter', '_stage_clock',
                   '_player_x', '_player_y', '_aim_x', '_aim_y')]
        for state in range(4):
            self.hold_damage_state(state)
            self.put_many([('_old_keys', 0, 1), ('_keys', 0, 1)])
            self.key(7, 4, True); self.frame(); self.key(7, 4, False); self.frame()
            self.check(f'giant-state-{state}-ESC-pauses', self.read('_mode') == PAUSED and self.read('_pause_previous') == BOSS)
            before = self.snapshot(fields)
            for _ in range(3):
                self.frame(); self.visible()
            self.check(f'giant-state-{state}-pause-freezes-state', before == self.snapshot(fields), fields=len(fields))
            label = ''.join(chr(code-160) if 192 <= code <= 255 else '?' for code in self.block('VRAM', 0x3820, 32))
            self.check(f'giant-state-{state}-pause-label', 'PAUSED / ESC TO RESUME' in label, text=label.strip())
            self.key(7, 4, True); self.frame(); self.key(7, 4, False); self.frame()
            self.check(f'giant-state-{state}-ESC-resumes', self.read('_mode') == BOSS)

    def measure_rate(self):
        self.hold_damage_state(0)
        self.put_many([('_hurt_clock', 0, 1), ('_player_x', 128, 2), ('_player_y', 166, 2)])
        self.clear_entities()
        start_time, start_frames = self.clock(), self.read('_frame_counter', 2)
        self.remove_bp(); self.cmd('debug cont')
        self.until(lambda: self.clock() >= start_time+3.0, 'three seconds of free-running giant fight')
        self.stop_at()
        duration = self.clock()-start_time
        elapsed = (self.read('_frame_counter', 2)-start_frames) & 65535
        self.fps = dict(fps=round(elapsed/duration, 3), emulated_seconds=round(duration, 3), game_updates=elapsed,
                        workload='Free-running giant gun phase, ordinary enemy shots and player damage enabled; no firing input.')
        self.check('giant-free-running-native-update-rate', self.read('_mode') == BOSS and self.fps['fps'] > 15, **self.fps)

    def paused_hit_marker(self):
        """A paused half-upload must not move the hit marker to the next pose."""
        self.hold_damage_state(0)
        self.wait_frames(lambda: self.read('_world_phase') == 3 and self.read('_world_pending') == 0,
                         'left-to-right hull motion boundary', maximum=34)
        self.clear_entities()
        self.put_many([('_boss_flash', 3, 1), ('_giant_hit_part', 1, 1),
                       ('_old_keys', 0, 1), ('_keys', 0, 1)])
        self.key(7, 4, True); self.frame(); self.key(7, 4, False); self.frame()
        assert self.read('_mode') == PAUSED and self.read('_world_phase') == 3
        assert self.read('_world_pending') == 1 and self.read('_world_target') == 4
        self.visible()
        descriptor = re.search(r'static const Sprite bullet\s*=\s*\{(\d+),(\d+),\d+,\d+\}',
                               (ROOT/'src/assets.h').read_text())
        assert descriptor
        offset, count = int(descriptor[1]), int(descriptor[2])
        records = (ROOT/'assets/sprite-records.bin').read_bytes()[offset:offset+count*4]
        def expected_records(phase):
            x, y = self.motion[phase]['left']
            result = []
            for index in range(count):
                dx, dy, pattern, _ = records[index*4:index*4+4]
                if dx >= 128: dx -= 256
                if dy >= 128: dy -= 256
                px = x-3+dx
                py = self.video_rows[y*9//8-6]+dy
                early = 128 if px < 0 else 0
                if px < 0: px += 32
                result.append(bytes([(py-1)&255, px&255, pattern, 15|early]))
            return result
        active_base = int(self.cmd('debug read {VDP regs} 5'))*128
        attributes = self.block('VRAM', active_base, self.read('_sprite_count')*4)
        active = [attributes[index:index+4] for index in range(0, len(attributes), 4)]
        current, future = expected_records(3), expected_records(4)
        self.check('giant-paused-hit-marker-stays-on-visible-pose', all(record in active for record in current) and all(record not in active for record in future),
                   visible_phase=3, pending_phase=4, current_records=[list(record) for record in current], future_records=[list(record) for record in future])
        self.key(7, 4, True); self.frame(); self.key(7, 4, False); self.frame()
        assert self.read('_mode') == BOSS

    def shoot(self, part):
        """Place the craft at a legal aim position; keyboard fire calls ROM hit logic."""
        phase = self.read('_world_target') if self.read('_world_pending') == 1 else self.read('_world_phase')
        x, y = self.motion[phase][part]
        player_x = min(range(20, 237), key=lambda value: abs(128+int((value-128)*3/4)-x))
        player_y = min(range(119, 182), key=lambda value: abs(self.video_rows[84+(value-119)*3//4]-y))
        self.put_many([('_player_x', player_x, 2), ('_player_y', player_y, 2),
                       ('_shot_clock', 0, 1), ('_old_keys', 0, 1), ('_keys', 0, 1)])
        self.key(8, 1, True); self.frame(); self.key(8, 1, False)
        assert self.read('_shot_clock') == 4, 'Keyboard did not execute player_fire'
        return dict(part=part, physical_target=[x, y], player_position=[player_x, player_y], target_phase=phase)

    def pause_transit(self, tick, scene):
        """ESC must preserve the dying hull, and must not resurrect it later."""
        assert self.read('_mode') == TRANSIT and self.read('_transition_clock') == tick
        assert self.read('_world_loaded') == scene
        self.put_many([('_old_keys', 0, 1), ('_keys', 0, 1)])
        self.key(7, 4, True); self.frame(); self.key(7, 4, False); self.frame()
        self.check(f'giant-transit-{tick}-ESC-pauses', self.read('_mode') == PAUSED and self.read('_pause_previous') == TRANSIT and self.read('_transition_clock') == tick)
        # Let both SAT buffers receive the unchanged paused objects and the
        # HUD receive its pause label before comparing the entire VRAM image.
        self.frame()
        fields = [(name, 1) for name in ('_mode', '_pause_previous', '_transition_clock',
                  '_giant_phase', '_giant_left_hp', '_giant_right_hp', '_giant_core_hp',
                  '_giant_gate_clock', '_world_loaded', '_world_phase', '_world_pending',
                  '_world_target', '_world_page', '_world_boss_state', '_world_boss_display_state')]
        fields += [(name, 2) for name in ('_boss_clock', '_frame_counter', '_stage_clock')]
        before = self.snapshot(fields)
        vram = self.block('VRAM', 0, 16384)
        for _ in range(3):
            self.frame()
            assert self.snapshot(fields) == before, 'Destruction pause changed game/world state'
            assert self.block('VRAM', 0, 16384) == vram, 'Destruction pause changed VRAM'
        visible_scene = self.read('_world_loaded')
        if scene == 5:
            self.check(f'giant-transit-{tick}-paused-hull-stays-destroyed', visible_scene == 5 and self.read('_world_boss_display_state') == 3)
            self.visible()
        else:
            self.check(f'giant-transit-{tick}-paused-road-does-not-resurrect-hull', visible_scene == 4)
            base = int(self.cmd('debug read {VDP regs} 2'))*1024
            road = np.load(ROOT/'assets/frames-4.npy')
            assert np.array_equal(decode_screen(vram, base)[16:176], road[self.read('_world_phase'), 16:176])
        self.check(f'giant-transit-{tick}-pause-freezes-full-VRAM-and-clock', True, checked_VRAM_bytes=16384, stopped_game_tick=tick, scene=scene)
        self.key(7, 4, True); self.frame(); self.key(7, 4, False)
        self.check(f'giant-transit-{tick}-ESC-resumes-without-scene-reload', self.read('_mode') == TRANSIT and self.read('_transition_clock') == tick and self.read('_world_loaded') == scene and self.read('_world_phase') == before['_world_phase'] and self.read('_world_pending') == before['_world_pending'])
        self.frame()
        assert self.read('_transition_clock') == tick+1

    def fight_and_clear(self):
        self.hold_damage_state(0)
        self.put_many([('_score', 0, 2), ('_giant_hit_part', 0, 1), ('_hurt_clock', 0, 1)])
        before = self.snapshot([('_giant_left_hp', 1), ('_giant_right_hp', 1), ('_giant_core_hp', 1), ('_score', 2)])
        evidence = self.shoot('core')
        self.check('giant-closed-core-rejects-real-keyboard-shot', before == self.snapshot([('_giant_left_hp', 1), ('_giant_right_hp', 1), ('_giant_core_hp', 1), ('_score', 2)]), **evidence)
        # Boundary HP values shorten the fight without bypassing targeting,
        # native part destruction, damage-state selection or opening timing.
        self.put_many([('_giant_left_hp', 1, 1), ('_giant_right_hp', 1, 1), ('_boss_hp', 118, 2)])
        self.clear_entities()
        evidence = self.shoot('left')
        self.check('giant-left-cannon-native-final-hit', self.read('_giant_left_hp') == 0 and self.read('_giant_right_hp') == 1 and self.read('_giant_phase') == 1 and self.read('_world_boss_state') == 1,
                   seeded_part_HP=1, **evidence)
        self.wait_frames(lambda: self.read('_world_boss_display_state') == 1, 'left damage becomes visible', maximum=4)
        self.visible(); self.capture(OUT/'giant-left-destroyed.png')
        evidence = self.shoot('right')
        self.check('giant-right-cannon-native-final-hit', self.read('_giant_left_hp') == 0 and self.read('_giant_right_hp') == 0 and self.read('_giant_phase') == 2 and self.read('_giant_gate_clock') == 0,
                   seeded_part_HP=1, **evidence)
        for tick in range(1, 24):
            self.frame()
            assert self.read('_giant_phase') == 2 and self.read('_giant_gate_clock') == tick
        self.frame()
        self.check('giant-core-opening-lasts-24-native-ticks', self.read('_giant_phase') == 3 and self.read('_giant_gate_clock') == 24 and self.read('_world_boss_display_state') == 3)
        self.visible(); self.capture(OUT/'giant-core-open.png')
        self.put_many([('_giant_core_hp', 1, 1), ('_boss_hp', 1, 2)])
        score_before = self.read('_score', 2)
        evidence = self.shoot('core')
        self.check('giant-core-native-final-hit-starts-destruction', self.read('_mode') == TRANSIT and self.read('_giant_phase') == 4 and self.read('_boss_hp', 2) == 0 and self.read('_transition_clock') == 1 and self.read('_score', 2) == score_before+702,
                   seeded_core_HP=1, **evidence)
        self.wait_frames(lambda: self.read('_transition_clock') == 10, 'destruction frame 10', maximum=12)
        self.pause_transit(10, 5)
        self.wait_frames(lambda: self.read('_transition_clock') == 39, 'destruction frame 39', maximum=40)
        self.check('giant-hull-remains-during-destruction', self.read('_mode') == TRANSIT and self.read('_world_loaded') == 5, transition_clock=39)
        self.pause_transit(39, 5)
        assert self.read('_transition_clock') == 40
        self.frame()
        self.check('giant-hull-removal-after-rendering-transit-40', self.read('_world_loaded') == 4 and self.read('_mode') == TRANSIT and self.read('_transition_clock') == 41,
                   note='draw_frame at clock 40 restores the road; next update reaches clock 41 before this breakpoint.')
        native = self.block('VRAM', 0, 16384)
        base = int(self.cmd('debug read {VDP regs} 2'))*1024
        road = np.load(ROOT/'assets/frames-4.npy')
        self.check('giant-hull-removal-restores-exact-native-road', np.array_equal(decode_screen(native, base)[16:176], road[self.read('_world_phase'), 16:176]))
        self.pause_transit(41, 4)
        self.wait_frames(lambda: self.read('_transition_clock') == 89, 'last transit tick', maximum=52)
        score_before = self.read('_score', 2)
        reward = self.read('_shield')*100+self.read('_bombs')*200
        self.frame()
        self.check('giant-clears-at-transit-tick-90', self.read('_mode') == CLEAR and self.read('_transition_clock') == 0 and self.read('_score', 2) == score_before+reward,
                   clear_reward=reward)
        for _ in range(5):
            self.frame()
        self.check('giant-clear-reward-is-not-repeated', self.read('_score', 2) == score_before+reward)
        self.capture(OUT/'giant-ending.png'); self.captures.append('giant-ending.png')

    def collision_and_retry(self):
        # Fresh ordinary entry avoids inheriting TRANSIT protection or a
        # destroyed hull from the preceding clear test.
        self.entry()
        self.put_many([('_shield', 1, 1), ('_hurt_clock', 0, 1), ('_bomb_flash', 0, 1)])
        self.clear_entities()
        x, y = self.read('_player_x', 2)*4, (self.read('_player_y', 2)-3)*4
        projectile = [1, x & 255, x >> 8, y & 255, y >> 8, 0, 0, 0, 0]
        self.cmd(';'.join(f'debug write memory {self.symbols["_shots"]+i} {value}' for i, value in enumerate(projectile)))
        self.frame()
        self.check('giant-native-projectile-collision-game-over', self.read('_mode') == OVER and self.read('_shield') == 0)
        self.frame()
        self.check('giant-game-over-keeps-hull-visible', self.read('_world_loaded') == 5)
        self.visible()
        self.capture(OUT/'giant-game-over.png'); self.captures.append('giant-game-over.png')
        self.put_many([('_transition_clock', 40, 1), ('_old_keys', 0, 1), ('_keys', 0, 1)])
        self.key(8, 1, True); self.frame(); self.key(8, 1, False)
        self.check('giant-game-over-real-fire-retry', self.read('_mode') == PLAY and self.read('_stage') == 0 and self.read('_shield') == 6 and self.read('_bombs') == 3 and self.read('_score', 2) == 0)
        self.check('giant-retry-clears-encounter-state', all(self.read(name) == 0 for name in ('_giant_phase', '_giant_left_hp', '_giant_right_hp', '_giant_core_hp', '_giant_gate_clock', '_giant_hit_part', '_world_boss_state')))
        self.wait_frames(lambda: self.read('_world_loaded') == 0, 'retry loads Episode 0', maximum=3)

    def run(self):
        self.cmd('set pause off;set speed 100;set limitsprites true;set accuracy pixel;set videosource MSX')
        self.cmd(TIMING_SETUP)
        self.emulator = self.cmd('openmsx_info version')
        self.check('giant-native-target-machine', self.cmd('machine_info config_name') == MACHINE and VDP in self.cmd('machine_info device VDP'), machine=MACHINE, VDP=VDP)
        self.check('giant-native-physical-memory', int(self.cmd('debug size {physical VRAM}')) == 16384 and int(self.cmd('debug size {Main RAM}')) == 32768)
        self.check('giant-native-standard-Z80', int(self.cmd('machine_info z80_freq')) == 3579545)
        self.check('giant-native-sprite-limit', self.cmd('set limitsprites') == 'true')
        executed = bytes.fromhex(self.cmd('binary encode hex [debug read_block [lsearch -inline [debug list] {*'+self.manifest['file']+'}] 0 524288]'))
        self.check('giant-executed-ROM-sha256', hashlib.sha256(executed).hexdigest() == self.manifest['sha256'], sha256=hashlib.sha256(executed).hexdigest())
        self.stop_at()
        self.release_keys()
        self.check('giant-check-starts-from-title', self.read('_mode') == 0)
        self.put_many([('_old_keys', 0, 1), ('_keys', 0, 1)])
        self.key(8, 1, True); self.frame(); self.key(8, 1, False)
        self.check('giant-check-real-fire-starts-new-game', self.read('_mode') == PLAY and self.read('_stage') == 0 and self.read('_shield') == 6 and self.read('_bombs') == 3)
        self.wait_frames(lambda: self.read('_world_loaded') == 0, 'initial game world', maximum=3)
        self.entry()
        self.all_visual_states()
        self.mid_transfer_state_changes()
        self.pauses()
        self.paused_hit_marker()
        self.measure_rate()
        self.fight_and_clear()
        self.collision_and_retry()
        violations = int(self.cmd('set ::neon_fast_vram_count'))
        self.check('giant-no-too-fast-VRAM-access', violations == 0, violations=violations)

    def report(self, error=None):
        return dict(passed=error is None, error=error, emulator=self.emulator, rom=self.manifest,
                    machine=MACHINE, video_standard=STANDARD, VDP=VDP,
                    physical_ram_bytes=32768, physical_vram_bytes=16384, physical_hardware_tested=False,
                    scenario_seeding='RAM selects final-stage clock 1198, damage-state scenarios, legal craft aiming positions, one-hit boundary HP and one overlapping enemy projectile. Keyboard fire, ESC, warning/opening clocks, damage, destruction, clear and retry execute in ROM. This is not a manual or keyboard-only full playthrough.',
                    screenshot_source='openMSX raw native screenshots; background proof independently decodes full 16 KiB VRAM readbacks at ROM breakpoints.',
                    animation_timing={'giant-native.gif': '32 consecutive native frames with measured emulated durations',
                                      'giant-damage-states-native.gif': '32 native captures across four seeded states, presented at 160 ms per sample'},
                    fps=self.fps, captures=self.captures, results=self.results)


def main():
    test = NativeBoss()
    error = None
    try:
        test.run()
    except Exception as exception:
        error = repr(exception)
        raise
    finally:
        (OUT/'giant-verification.json').write_text(json.dumps(test.report(error), indent=2)+'\n', encoding='utf-8')
        try:
            test.release_keys()
            test.remove_bp()
            test.cmd('if {[debug breaked]} {debug cont}')
        except Exception:
            pass
    print('ALL NATIVE GIANT CHECKS PASSED')


if __name__ == '__main__':
    main()
