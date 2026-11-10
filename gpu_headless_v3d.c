/* Headless V3D GLES2 workload v1.2; no HDMI/DRM master needed.
   Actual GL_RENDERER must report V3D/VideoCore; otherwise exits nonzero.
   compile: cc -O2 -Wall -Wextra gpu_headless_v3d.c -o gpu_headless_v3d -lEGL -lGLESv2 -lgbm -lm */
#define _POSIX_C_SOURCE 200809L
#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <GLES2/gl2.h>
#include <gbm.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#ifndef EGL_PLATFORM_GBM_KHR
#define EGL_PLATFORM_GBM_KHR 0x31D7
#endif
#ifndef EGL_PLATFORM_SURFACELESS_MESA
#define EGL_PLATFORM_SURFACELESS_MESA 0x31DD
#endif
#ifndef EGL_NO_CONFIG_KHR
#define EGL_NO_CONFIG_KHR ((EGLConfig)0)
#endif
static volatile sig_atomic_t running=1;
static void on_signal(int s) {(void)s;running=0;}
static double monotime(void) {struct timespec t; clock_gettime(CLOCK_MONOTONIC,&t);return (double)t.tv_sec+t.tv_nsec*1e-9;}
static GLuint shader(GLenum type,const char *src){
 GLuint s=glCreateShader(type);glShaderSource(s,1,&src,NULL);glCompileShader(s);
 GLint ok=0;glGetShaderiv(s,GL_COMPILE_STATUS,&ok);
 if(!ok){char b[4096]={0};glGetShaderInfoLog(s,sizeof b,NULL,b);fprintf(stderr,"shader compile error: %s\n",b);glDeleteShader(s);return 0;}
 return s;
}
static const char *vs="attribute vec2 pos;varying vec2 uv;void main(){uv=pos*.5+.5;gl_Position=vec4(pos,0.,1.);}";
static const char *fs=
 "precision highp float;varying vec2 uv;uniform float tick;void main(){"
 "vec2 v=uv*11.0+vec2(tick*0.005);float c=0.0;"
 "for(int i=0;i<48;i++){"
 "v=fract(mat2(1.13,-0.31,0.37,1.09)*v+vec2(sin(v.x+tick*.01),cos(v.y+tick*.01)));"
 "c+=dot(v,v)*.0104;}"
 "gl_FragColor=vec4(fract(c),fract(v.x+c),fract(v.y+tick*.01),1.0);}";
int main(int argc,char **argv){
 int width=960,height=540,duration=0,fd=-1,ok=0;
 for(int i=1;i<argc;i++){
  if(!strcmp(argv[i],"--width")&&i+1<argc)width=atoi(argv[++i]);
  else if(!strcmp(argv[i],"--height")&&i+1<argc)height=atoi(argv[++i]);
  else if(!strcmp(argv[i],"--seconds")&&i+1<argc)duration=atoi(argv[++i]);
  else {fprintf(stderr,"usage: %s [--width n] [--height n] [--seconds n; 0=until signal]\n",argv[0]);return 2;}
 }
 if(width<64||height<64||width>2560||height>1440||duration<0) return 2;
 signal(SIGTERM,on_signal);signal(SIGINT,on_signal);
 PFNEGLGETPLATFORMDISPLAYEXTPROC getdisplay=(PFNEGLGETPLATFORMDISPLAYEXTPROC)eglGetProcAddress("eglGetPlatformDisplayEXT");
 if(!getdisplay){fprintf(stderr,"EGL platform extension unavailable\n");return 3;}
 EGLDisplay d=EGL_NO_DISPLAY; struct gbm_device *gbm=NULL;
 /* GBM on render node is preferred: it avoids DRM/KMS master and fullscreen VT. */
 char node[64];
 for(int i=128;i<136;i++){
  snprintf(node,sizeof node,"/dev/dri/renderD%d",i);
  fd=open(node,O_RDWR|O_CLOEXEC);
  if(fd<0)continue;
  gbm=gbm_create_device(fd);
  if(gbm){d=getdisplay(EGL_PLATFORM_GBM_KHR,gbm,NULL);if(d!=EGL_NO_DISPLAY){EGLint ma,mi;if(eglInitialize(d,&ma,&mi)){fprintf(stderr,"EGL backend: GBM %s\n",node);break;}eglTerminate(d);}}
  if(gbm){gbm_device_destroy(gbm);gbm=NULL;} close(fd);fd=-1;d=EGL_NO_DISPLAY;
 }
 if(d==EGL_NO_DISPLAY){
  d=getdisplay(EGL_PLATFORM_SURFACELESS_MESA,EGL_DEFAULT_DISPLAY,NULL);
  EGLint ma,mi;
  if(d==EGL_NO_DISPLAY||!eglInitialize(d,&ma,&mi)){fprintf(stderr,"EGL init failed: 0x%x\n",eglGetError());return 3;}
  fprintf(stderr,"EGL backend: surfaceless (hardware validation follows)\n");
 }
 if(!eglBindAPI(EGL_OPENGL_ES_API)){fprintf(stderr,"eglBindAPI failed 0x%x\n",eglGetError());goto cleanup;}
 EGLint configs=0;
 if(!eglGetConfigs(d,NULL,0,&configs)){fprintf(stderr,"eglGetConfigs failed 0x%x\n",eglGetError());goto cleanup;}
 const char *ext=eglQueryString(d,EGL_EXTENSIONS);
 int surfaceless=ext&&strstr(ext,"EGL_KHR_surfaceless_context")!=NULL;
 int configless=ext&&(strstr(ext,"EGL_KHR_no_config_context")!=NULL || strstr(ext,"EGL_MESA_configless_context")!=NULL);
 fprintf(stderr,"EGL configs=%d, KHR_surfaceless=%s, configless=%s\n",configs,surfaceless?"yes":"no",configless?"yes":"no");
 const EGLint ctxattr[]={EGL_CONTEXT_CLIENT_VERSION,2,EGL_NONE};
 EGLConfig cfg=NULL;EGLint num=0;
 EGLContext ctx=EGL_NO_CONTEXT;
 EGLSurface surf=EGL_NO_SURFACE;
 /* Do not require PBUFFER_BIT here: render node GBM may offer window-only
    EGLConfigs. We draw into a GLES FBO, so no native window is required. */
 const EGLint relaxed[]={EGL_SURFACE_TYPE,0,EGL_RENDERABLE_TYPE,EGL_OPENGL_ES2_BIT,EGL_NONE};
 if(eglChooseConfig(d,relaxed,&cfg,1,&num) && num>0){
    ctx=eglCreateContext(d,cfg,EGL_NO_CONTEXT,ctxattr);
    if(ctx==EGL_NO_CONTEXT) fprintf(stderr,"EGL GLES2 context on config failed: 0x%x\n",eglGetError());
 } else {
    fprintf(stderr,"No GLES2 config: count=%d, EGL error 0x%x\n",num,eglGetError());
 }
 if(ctx==EGL_NO_CONTEXT && configless){
    ctx=eglCreateContext(d,EGL_NO_CONFIG_KHR,EGL_NO_CONTEXT,ctxattr);
    if(ctx!=EGL_NO_CONTEXT) fprintf(stderr,"EGL context: configless\n");
    else fprintf(stderr,"Configless EGL context failed: 0x%x\n",eglGetError());
 }
 if(ctx==EGL_NO_CONTEXT){fprintf(stderr,"ERROR: cannot create OpenGL ES2 context\n");goto cleanup;}
 if(surfaceless){
    if(!eglMakeCurrent(d,EGL_NO_SURFACE,EGL_NO_SURFACE,ctx)){
        fprintf(stderr,"Surfaceless eglMakeCurrent failed: 0x%x\n",eglGetError());
    } else fprintf(stderr,"EGL surface: EGL_NO_SURFACE + FBO\n");
 }
 /* Legacy fallback to 1x1 pbuffer, only if a surface-less context was not
    made current and the driver advertises PBUFFER-capable EGL configs. */
 if(eglGetCurrentContext()==EGL_NO_CONTEXT){
    const EGLint pbconf[]={EGL_SURFACE_TYPE,EGL_PBUFFER_BIT,EGL_RENDERABLE_TYPE,EGL_OPENGL_ES2_BIT,EGL_NONE};
    EGLConfig pbcfg=NULL;EGLint pbn=0;
    if(eglChooseConfig(d,pbconf,&pbcfg,1,&pbn)&&pbn>0){
        if(ctx!=EGL_NO_CONTEXT) eglDestroyContext(d,ctx);
        ctx=eglCreateContext(d,pbcfg,EGL_NO_CONTEXT,ctxattr);
        const EGLint pb[]={EGL_WIDTH,1,EGL_HEIGHT,1,EGL_NONE};
        if(ctx!=EGL_NO_CONTEXT)surf=eglCreatePbufferSurface(d,pbcfg,pb);
        if(surf!=EGL_NO_SURFACE && eglMakeCurrent(d,surf,surf,ctx)){
            fprintf(stderr,"EGL surface: 1x1 pbuffer fallback\n");
        }else{
            fprintf(stderr,"Fallback pbuffer failed: 0x%x\n",eglGetError());
        }
    }
 }
 if(eglGetCurrentContext()==EGL_NO_CONTEXT){
    fprintf(stderr,"ERROR: no usable EGL surface/context on this driver\n");
    if(surf!=EGL_NO_SURFACE)eglDestroySurface(d,surf);
    if(ctx!=EGL_NO_CONTEXT)eglDestroyContext(d,ctx);
    goto cleanup;
 }
 const char *renderer=(const char *)glGetString(GL_RENDERER);
 printf("GL_RENDERER: %s\n",renderer?renderer:"(null)");fflush(stdout);
 if(!renderer||(!strstr(renderer,"V3D")&&!strstr(renderer,"VideoCore")&&!strstr(renderer,"VC4"))){fprintf(stderr,"Not hardware V3D; GPU test invalid\n");goto gl_cleanup;}
 GLuint vertex=shader(GL_VERTEX_SHADER,vs),fragment=shader(GL_FRAGMENT_SHADER,fs);
 if(!vertex||!fragment)goto gl_cleanup;
 GLuint program=glCreateProgram();glAttachShader(program,vertex);glAttachShader(program,fragment);glBindAttribLocation(program,0,"pos");glLinkProgram(program);
 GLint linked=0;glGetProgramiv(program,GL_LINK_STATUS,&linked);
 if(!linked){char b[4096]={0};glGetProgramInfoLog(program,sizeof b,NULL,b);fprintf(stderr,"shader link: %s\n",b);goto gl_cleanup;}
 glUseProgram(program);
 GLint tick=glGetUniformLocation(program,"tick");
 GLuint texture,fbo;glGenTextures(1,&texture);glBindTexture(GL_TEXTURE_2D,texture);
 glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
 glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA,width,height,0,GL_RGBA,GL_UNSIGNED_BYTE,NULL);
 glGenFramebuffers(1,&fbo);glBindFramebuffer(GL_FRAMEBUFFER,fbo);
 glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,texture,0);
 if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE){fprintf(stderr,"FBO incomplete\n");goto gl_cleanup;}
 GLfloat quad[]={-1.f,-1.f,1.f,-1.f,-1.f,1.f,1.f,1.f};
 glVertexAttribPointer(0,2,GL_FLOAT,GL_FALSE,0,quad);glEnableVertexAttribArray(0);
 glViewport(0,0,width,height);double begin=monotime(),last=begin;
 unsigned long frames=0;
 while(running&&(duration==0||monotime()-begin<duration)){
  glUniform1f(tick,(float)(frames%100000));glDrawArrays(GL_TRIANGLE_STRIP,0,4);glFinish();frames++;
  if(glGetError()!=GL_NO_ERROR){fprintf(stderr,"GPU draw error\n");break;}
  double now=monotime();if(now-last>=2){fprintf(stdout,"gpu frames=%lu t=%.1fs fps=%.1f\n",frames,now-begin,frames/(now-begin));fflush(stdout);last=now;}
 }
 fprintf(stdout,"GPU_DRAW_FRAMES: %lu\n",frames);fflush(stdout);
 if(frames>0)ok=1;
 glDeleteFramebuffers(1,&fbo);glDeleteTextures(1,&texture);
 glDeleteProgram(program);glDeleteShader(vertex);glDeleteShader(fragment);
 gl_cleanup:
 eglMakeCurrent(d,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT);
 if(surf!=EGL_NO_SURFACE)eglDestroySurface(d,surf);eglDestroyContext(d,ctx);
 cleanup:
 eglTerminate(d);
 if(gbm)gbm_device_destroy(gbm);
 if(fd>=0)close(fd);
 return ok?0:4;
}
