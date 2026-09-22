source [file join [file dirname [info script]] launch.tcl]
after time 6 {openmsx::internal_screenshot -raw ../../outputs/launcher-title.png}
after time 7 {keymatrixdown 8 1}
after time 7.3 {keymatrixup 8 1}
after time 10 {keymatrixdown 8 128}
after time 10.3 {keymatrixup 8 128}
after time 13 {
 if {[catch {
  set f [open launcher-check.txt w]
  puts $f "machine=[machine_info config_name]"
  puts $f "mode=[debug read memory 57344]"
  puts $f "stage=[debug read memory 57345]"
  puts $f "player_x=[debug read memory 57358]"
  puts $f "r800=[debug read {S1990 regs} 6]"
  close $f
  openmsx::internal_screenshot -raw ../../outputs/launcher-play.png
 } err]} {set f [open launcher-error.txt w];puts $f $err;close $f}
 exit
}
