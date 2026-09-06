# Local developer command mailbox, using only openMSX's supported Tcl API.
set bridge_dir [file normalize [file join [file dirname [info script]] .. work]]
set renderer SDLGL-PP
catch {set videosource {Sunrise GFX9000}}
set pause off
proc poll_bridge {} {
    global bridge_dir
    set request [file join $bridge_dir emu-request.tcl]
    if {[file exists $request]} {
        set status [catch {source $request} value]
        file delete $request
        set f [open [file join $bridge_dir emu-response.txt] w]
        puts $f "$status\n$value"
        close $f
    }
    after realtime 0.05 poll_bridge
}
poll_bridge
