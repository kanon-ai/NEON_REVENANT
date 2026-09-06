# Controller-only native campaign exercise. The caller supplies ::sym as a
# Tcl dict mapping linker symbol names to addresses, then sources this file.
# Game RAM is observed but never changed. No speed setting is changed here.
if {![info exists ::sym]} { error "autoplay requires the ::sym address dict" }
if {[namespace exists ::autoplay]} { catch {::autoplay::stop replaced} }
namespace eval ::autoplay {
    variable timer ""
    variable started [machine_info time]
    variable first_frame 0
    variable last_frame 0
    variable frame_total 0
    variable tick_count 0
    variable bomb_until 0.0
    variable last_bomb -100.0
    variable running 1
}
set ::autoplay_result [dict create status running]

proc ::autoplay::byte_at {address} {
    return [debug read memory $address]
}
proc ::autoplay::word_at {address} {
    return [expr {[byte_at $address] | ([byte_at [expr {$address+1}]] << 8)}]
}
proc ::autoplay::signed_at {address} {
    set value [word_at $address]
    return [expr {$value >= 32768 ? $value-65536 : $value}]
}
proc ::autoplay::read8 {name} {
    return [byte_at [dict get $::sym $name]]
}
proc ::autoplay::read16 {name} {
    return [word_at [dict get $::sym $name]]
}
proc ::autoplay::clamp {value low high} {
    if {$value < $low} { return $low }
    if {$value > $high} { return $high }
    return $value
}
proc ::autoplay::keys {directions fire bomb} {
    keymatrixup 8 241
    keymatrixup 5 32
    set mask [expr {$directions | ($fire ? 1 : 0)}]
    if {$mask} { keymatrixdown 8 $mask }
    if {$bomb} { keymatrixdown 5 32 }
}
proc ::autoplay::stop {reason} {
    variable timer
    variable started
    variable frame_total
    variable tick_count
    variable running
    set running 0
    if {$timer ne ""} { catch {after cancel $timer}; set timer "" }
    keys 0 0 0
    set ::autoplay_result [dict create status $reason \
        elapsed_seconds [expr {[machine_info time]-$started}] \
        game_frames $frame_total controller_ticks $tick_count \
        mode [read8 _mode] stage [expr {[read8 _stage]+1}] \
        score [read16 _score] shield [read8 _shield] bombs [read8 _bombs] \
        boss_hp [read16 _boss_hp] \
        controls_only 1 game_ram_modified 0]
    return $::autoplay_result
}
proc ::autoplay::tick {} {
    variable timer
    variable started
    variable first_frame
    variable last_frame
    variable frame_total
    variable tick_count
    variable bomb_until
    variable last_bomb
    variable running
    set timer ""
    if {!$running} { return }
    set caught [catch {
        set now [machine_info time]
        set mode [read8 _mode]
        set frame [read16 _frame_counter]
        if {$tick_count} { incr frame_total [expr {($frame-$last_frame)&65535}] }
        set last_frame $frame
        incr tick_count
        if {$mode == 5} { stop clear; return }
        if {$mode == 4} { stop game_over; return }
        if {$now-$started > 480.0} { stop timeout; return }

        set px [read16 _player_x]
        set py [read16 _player_y]
        set target_x 128
        set target_y 166
        if {$mode == 2} {
            set tx [read16 _boss_x]
            set ty [read16 _boss_y]
            set target_x [clamp [expr {128+($tx-128)*4/3}] 20 236]
            set target_y [clamp [expr {119+($ty-84)*4/3}] 119 181]
        } elseif {$mode == 1} {
            set best_z -1
            set base [dict get $::sym _foes]
            for {set i 0} {$i < 9} {incr i} {
                set address [expr {$base+12*$i}]
                if {![byte_at $address]} { continue }
                set z [byte_at [expr {$address+2}]]
                set tx [signed_at [expr {$address+8}]]
                set ty [signed_at [expr {$address+10}]]
                if {$z > $best_z} {
                    set best_z $z
                    set target_x [clamp [expr {128+($tx-128)*4/3}] 20 236]
                    set target_y [clamp [expr {119+($ty-84)*4/3}] 119 181]
                }
            }
        }

        set danger 0
        set nearest_dx 0
        set base [dict get $::sym _shots]
        for {set i 0} {$i < 14} {incr i} {
            set address [expr {$base+9*$i}]
            if {![byte_at $address]} { continue }
            set bx [expr {[signed_at [expr {$address+1}]]/4}]
            set by [expr {[signed_at [expr {$address+3}]]/4}]
            if {abs($bx-$px)<22 && abs($by-$py)<28} {
                incr danger
                set nearest_dx [expr {$bx-$px}]
            }
        }
        if {$danger && [read8 _hurt_clock] == 0} {
            # A small lateral escape still keeps the broad boss hitbox aimed.
            set target_x [clamp [expr {$px+($nearest_dx>=0 ? -20 : 20)}] 20 236]
        }
        set use_bomb [expr {$now<$bomb_until}]
        if {$mode in {1 2} && [read8 _bombs] && $now-$last_bomb>2.5 &&
            (($danger && [read8 _shield]<=3) ||
             ($mode==2 && [read16 _boss_hp]>25))} {
            set last_bomb $now
            set bomb_until [expr {$now+0.12}]
            set use_bomb 1
        }
        set directions 0
        if {$px>$target_x+3} { set directions [expr {$directions|16}] }
        if {$px<$target_x-3} { set directions [expr {$directions|128}] }
        if {$py>$target_y+2} { set directions [expr {$directions|32}] }
        if {$py<$target_y-2} { set directions [expr {$directions|64}] }
        # Holding Space starts a fresh title and shoots throughout gameplay.
        keys $directions 1 $use_bomb
    } error options]
    if {$caught == 1} {
        catch {stop error}
        dict set ::autoplay_result error $error
        return
    }
    if {$running} { set timer [after time 0.033 ::autoplay::tick] }
}

::autoplay::keys 0 0 0
set ::autoplay::first_frame [::autoplay::read16 _frame_counter]
set ::autoplay::last_frame $::autoplay::first_frame
set ::autoplay::timer [after time 0.05 ::autoplay::tick]
