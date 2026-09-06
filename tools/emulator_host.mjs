// Local-only openMSX control bridge for development. BIOS stays in its existing installation.
import {spawn} from 'node:child_process';
import {createServer as netServer} from 'node:net';
import {createServer as httpServer} from 'node:http';
import {appendFileSync} from 'node:fs';
const name='neon-revenant-'+process.pid;
let sock,buf='',pending=[],child;
const enc=s=>s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
const dec=s=>s.replaceAll('&lt;','<').replaceAll('&gt;','>').replaceAll('&quot;','"').replaceAll('&amp;','&');
function command(s){return new Promise((resolve,reject)=>{pending.push({resolve,reject});sock.write('<command>'+enc(s)+'</command>\n');});}
const pipe=netServer(s=>{sock=s;s.setEncoding('utf8');s.on('data',d=>{appendFileSync('work/emulator-xml.log',d);buf+=d;let m;while((m=buf.match(/<reply\s+result="(ok|nok)">([\s\S]*?)<\/reply>/))){buf=buf.slice(m.index+m[0].length);let p=pending.shift();if(p)(m[1]==='ok'?p.resolve:p.reject)(dec(m[2]));}});s.write('<openmsx-control>\n');console.log('CONNECTED');});
pipe.listen('\\\\.\\pipe\\'+name,()=>{
 child=spawn(process.env.OPENMSX_EXE||'C:\\Program Files\\openMSX\\openmsx.exe',['-control','pipe:'+name,'-machine','Panasonic_FS-A1ST','-ext','gfx9000',...process.argv.slice(2)],{windowsHide:true,stdio:['ignore','pipe','pipe']});
 child.stdout.on('data',d=>process.stdout.write(d));child.stderr.on('data',d=>process.stderr.write(d));
 child.on('exit',()=>{pipe.close();server.close();process.exit();});
});
const server=httpServer(async(req,res)=>{if(req.method!=='POST'){res.writeHead(405);res.end();return;}let b='';for await(const c of req)b+=c;try{let v=await command(b);res.writeHead(200,{'Content-Type':'text/plain; charset=utf-8'});res.end(v);}catch(e){res.writeHead(500);res.end(String(e));}}).listen(18790,'127.0.0.1');
