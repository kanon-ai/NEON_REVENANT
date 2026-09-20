// Local-only 32 KiB MSX1 test bridge. Set MSX_VIDEO_STANDARD=ntsc or pal.
// The local profile contains only configuration; BIOS stays in the existing installation.
import {spawn} from 'node:child_process';
import {createServer as netServer} from 'node:net';
import {createServer as httpServer} from 'node:http';
import {appendFileSync, mkdirSync, copyFileSync, writeFileSync, readFileSync} from 'node:fs';
import {dirname, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
const toolDir=dirname(fileURLToPath(import.meta.url));
const standard=(process.env.MSX_VIDEO_STANDARD||'ntsc').toLowerCase();
if(!['ntsc','pal'].includes(standard))throw new Error('MSX_VIDEO_STANDARD must be ntsc or pal');
const ramKiB=Number(process.env.MSX_RAM_KIB||32);
if(![32,64].includes(ramKiB))throw new Error('MSX_RAM_KIB must be 32 or 64');
const machine='NEON_MSX1_RAM'+ramKiB+'_'+standard.toUpperCase();
const profile=resolve(toolDir,'../work/ram'+ramKiB+'-profile-'+standard);
mkdirSync(resolve(profile,'machines'),{recursive:true});
const sourceMachine=resolve(toolDir,'machines','NEON_MSX1_RAM32_'+standard.toUpperCase()+'.xml');
if(ramKiB===32)copyFileSync(sourceMachine,resolve(profile,'machines',machine+'.xml'));
else writeFileSync(resolve(profile,'machines',machine+'.xml'),readFileSync(sourceMachine,'utf8').replace('RAM32','RAM64').replace('32 KiB RAM at 8000h-FFFFh','64 KiB RAM at 0000h-FFFFh').replace('<mem base="0x8000" size="0x8000"/>','<mem base="0x0000" size="0x10000"/>'));
process.env.OPENMSX_USER_DATA=profile;
process.env.SDL_AUDIODRIVER=process.env.SDL_AUDIODRIVER||'dummy';
const settingsPath=resolve(profile,'verification-settings.xml');
writeFileSync(settingsPath,'<!DOCTYPE settings SYSTEM "settings.dtd">\n<settings><settings><setting id="renderer">none</setting></settings><bindings/><shortcuts/></settings>\n');
const logPath=resolve(profile,'emulator-xml.log');
const name='neon-revenant-'+process.pid;
const port=18801;
let sock,buf='',pending=[],child;
const enc=s=>s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
const dec=s=>s.replaceAll('&lt;','<').replaceAll('&gt;','>').replaceAll('&quot;','"').replaceAll('&amp;','&');
function command(s){return new Promise((resolve,reject)=>{pending.push({resolve,reject});sock.write('<command>'+enc(s)+'</command>\n');});}
const pipe=netServer(s=>{sock=s;s.setEncoding('utf8');s.on('data',d=>{appendFileSync(logPath,d);buf+=d;let m;while((m=buf.match(/<reply\s+result="(ok|nok)">([\s\S]*?)<\/reply>/))){buf=buf.slice(m.index+m[0].length);let p=pending.shift();if(p)(m[1]==='ok'?p.resolve:p.reject)(dec(m[2]));}});s.write('<openmsx-control>\n');console.log('CONNECTED');});
pipe.listen('\\\\.\\pipe\\'+name,()=>{
 child=spawn(process.env.OPENMSX_EXE||'C:\\Program Files\\openMSX\\openmsx.exe',['-control','pipe:'+name,'-setting',settingsPath,'-machine',machine,'-command','set renderer none;set power off',...process.argv.slice(2)],{windowsHide:true,stdio:['ignore','pipe','pipe']});
 child.stdout.on('data',d=>process.stdout.write(d));child.stderr.on('data',d=>process.stderr.write(d));
 child.on('exit',()=>{pipe.close();server.close();process.exit();});
});
const server=httpServer(async(req,res)=>{
 // CLI clients only: browsers must never send arbitrary Tcl to this bridge.
 const host=(req.headers.host||'').toLowerCase();
 const browserRequest=Object.keys(req.headers).some(h=>h==='origin'||h.startsWith('sec-fetch-'));
 const reject=(status,message)=>{req.resume();res.writeHead(status);res.end(message);};
 if(browserRequest||(host!==`127.0.0.1:${port}`&&host!==`localhost:${port}`)){
  reject(403,'Only direct local CLI requests are allowed.');return;
 }
 if(req.method!=='POST'){reject(405,'POST required.');return;}
 if(!sock||sock.destroyed||!sock.writable){reject(503,'Emulator connection is not ready.');return;}
 let b='';for await(const c of req)b+=c;
 if(!sock||sock.destroyed||!sock.writable){reject(503,'Emulator connection is not ready.');return;}
 try{let v=await command(b);res.writeHead(200,{'Content-Type':'text/plain; charset=utf-8'});res.end(v);}
 catch(e){res.writeHead(500);res.end(String(e));}
}).listen(port,'127.0.0.1');
