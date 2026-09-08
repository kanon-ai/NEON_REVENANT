// Local-only openMSX control bridge for development. BIOS stays in its existing installation.
import {spawn} from 'node:child_process';
import {createServer as netServer} from 'node:net';
import {createServer as httpServer} from 'node:http';
import {appendFileSync,existsSync,mkdirSync,writeFileSync} from 'node:fs';
import {resolve,join} from 'node:path';
const name='neon-v9990-lab-'+process.pid;
const port=Number(process.env.NEON_EMU_PORT||18890);
const profile=resolve('work/emulator-profile');
const environment={...process.env,OPENMSX_HOME:process.env.OPENMSX_HOME||profile,
 OPENMSX_USER_DATA:process.env.OPENMSX_USER_DATA||join(profile,'user_data'),
 SDL_AUDIODRIVER:process.env.SDL_AUDIODRIVER||'dummy'};
for(const dir of ['work',environment.OPENMSX_HOME,environment.OPENMSX_USER_DATA])mkdirSync(dir,{recursive:true});
const settings=join(environment.OPENMSX_USER_DATA,'settings.xml');
if(!existsSync(settings))writeFileSync(settings,'<!DOCTYPE settings SYSTEM "settings.dtd">\n<settings><settings><setting id="renderer">none</setting><setting id="power">false</setting></settings></settings>\n');
let sock,buf='',pending=[],child;
const enc=s=>s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
const dec=s=>s.replaceAll('&lt;','<').replaceAll('&gt;','>').replaceAll('&quot;','"').replaceAll('&amp;','&');
function command(s){return new Promise((resolve,reject)=>{pending.push({resolve,reject});sock.write('<command>'+enc(s)+'</command>\n');});}
const pipe=netServer(s=>{sock=s;s.setEncoding('utf8');s.on('data',d=>{appendFileSync('work/emulator-xml.log',d);buf+=d;let m;while((m=buf.match(/<reply\s+result="(ok|nok)">([\s\S]*?)<\/reply>/))){buf=buf.slice(m.index+m[0].length);let p=pending.shift();if(p)(m[1]==='ok'?p.resolve:p.reject)(dec(m[2]));}});s.write('<openmsx-control>\n');console.log('CONNECTED');});
pipe.listen('\\\\.\\pipe\\'+name,()=>{
 child=spawn(process.env.OPENMSX_EXE||'C:\\Program Files\\openMSX\\openmsx.exe',['-control','pipe:'+name,'-machine','Panasonic_FS-A1ST','-ext','gfx9000',...process.argv.slice(2),'-command','set renderer SDLGL-PP','-command','set power on','-command','after time 0.1 {set videosource GFX9000}'],{env:environment,windowsHide:true,stdio:['ignore','pipe','pipe']});
 child.stdout.on('data',d=>process.stdout.write(d));child.stderr.on('data',d=>process.stderr.write(d));
 child.on('exit',()=>{pipe.close();server.close();process.exit();});
});
const server=httpServer(async(req,res)=>{
 const host=(req.headers.host||'').toLowerCase();
 const browserRequest=Object.keys(req.headers).some(h=>h==='origin'||h.startsWith('sec-fetch-'));
 const reject=(status,message)=>{req.resume();res.writeHead(status);res.end(message);};
 if(browserRequest||(host!==`127.0.0.1:${port}`&&host!==`localhost:${port}`)){
  reject(403,'Only direct local CLI requests are allowed.');return;
 }
 if(req.method!=='POST'){reject(405,'POST required.');return;}
 if(!sock||sock.destroyed||!sock.writable){reject(503,'Emulator connection is not ready.');return;}
 let b='';for await(const c of req)b+=c;
 try{let v=await command(b);res.writeHead(200,{'Content-Type':'text/plain; charset=utf-8'});res.end(v);}
 catch(e){res.writeHead(500);res.end(String(e));}
}).listen(port,'127.0.0.1');
