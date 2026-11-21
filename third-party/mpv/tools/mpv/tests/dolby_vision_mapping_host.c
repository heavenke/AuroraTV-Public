/* Compile against the locked host libplacebo with -Ddovi=enabled.
 * This verifies actual shader generation and the uniform-array bridge, including
 * both polynomial and maximum-order MMR branches. No video/network is needed.
 */
#define _GNU_SOURCE
#include <assert.h>
#include <stdbool.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <libplacebo/shaders/colorspace.h>

struct gl_shader_cache { char *uniforms, *header, *body; int count; };
static void append(char **out, const char *fmt, ...)
{
    va_list ap; va_start(ap, fmt); char *line = NULL;
    assert(vasprintf(&line, fmt, ap) >= 0); va_end(ap);
    size_t old = *out ? strlen(*out) : 0, n = strlen(line);
    *out = realloc(*out, old + n + 1); memcpy(*out + old, line, n + 1); free(line);
}
static void *talloc_new(void *ctx) { (void)ctx; return malloc(1); }
static char *talloc_strdup(void *ctx, const char *s) { (void)ctx; return strdup(s); }
static char *talloc_asprintf(void *ctx, const char *fmt, ...)
{
    (void)ctx; va_list ap; va_start(ap, fmt); char *out = NULL;
    assert(vasprintf(&out, fmt, ap) >= 0); va_end(ap); return out;
}
static void talloc_free(void *ctx) { free(ctx); }
static void gl_sc_uniform_dynamic(struct gl_shader_cache *sc) { (void)sc; }
static void uniform(struct gl_shader_cache *sc, char *name, const char *type)
{
    append(&sc->uniforms, "uniform %s %s;\n", type, name); sc->count++;
}
static void gl_sc_uniform_f(struct gl_shader_cache *sc, char *n, float v) { (void)v; uniform(sc,n,"float"); }
static void gl_sc_uniform_vec2(struct gl_shader_cache *sc, char *n, float *v) { (void)v; uniform(sc,n,"vec2"); }
static void gl_sc_uniform_vec3(struct gl_shader_cache *sc, char *n, float *v) { (void)v; uniform(sc,n,"vec3"); }
static void gl_sc_uniform_vec4(struct gl_shader_cache *sc, char *n, const float *v) { (void)v; uniform(sc,n,"vec4"); }
static void gl_sc_uniform_mat2(struct gl_shader_cache *sc, char *n, bool t, float *v) { (void)v;(void)t;uniform(sc,n,"mat2"); }
static void gl_sc_uniform_mat3(struct gl_shader_cache *sc, char *n, bool t, float *v) { (void)v;(void)t;uniform(sc,n,"mat3"); }
static void gl_sc_hadd(struct gl_shader_cache *sc, const char *s) { append(&sc->header,"%s",s); }
static void gl_sc_haddf(struct gl_shader_cache *sc, const char *fmt, ...)
{
    va_list ap;va_start(ap,fmt);char *s=NULL;assert(vasprintf(&s,fmt,ap)>=0);va_end(ap);
    gl_sc_hadd(sc,s);free(s);
}
static void gl_sc_addf(struct gl_shader_cache *sc, const char *fmt, ...)
{
    va_list ap;va_start(ap,fmt);char *s=NULL;assert(vasprintf(&s,fmt,ap)>=0);va_end(ap);
    append(&sc->body,"%s",s);free(s);
}
#define AURORA_DOVI_BRIDGE_ONLY
#include "../dolby_vision_mapping.inc"

int main(int argc, char **argv)
{
    assert(argc == 2);
    for (int mmr = 0; mmr < 3; mmr++) {
        struct pl_dovi_metadata dv = {0};
        dv.linear.m[0][0] = dv.linear.m[1][1] = dv.linear.m[2][2] = 1;
        dv.nonlinear.m[0][0] = dv.nonlinear.m[1][1] = dv.nonlinear.m[2][2] = 1;
        for (int c = 0; c < 3; c++) {
            dv.comp[c].num_pivots = 9;
            for (int i = 0; i < 9; i++) dv.comp[c].pivots[i] = i / 8.0f;
            for (int i = 0; i < 8; i++) {
                dv.comp[c].method[i] = mmr == 2 || (mmr == 1 && i % 2) ? 1 : 0;
                dv.comp[c].poly_coeffs[i][1] = 1;
                dv.comp[c].mmr_order[i] = 3;
                dv.comp[c].mmr_coeffs[i][0][c] = 1;
            }
        }
        struct pl_color_repr repr = {.sys=PL_COLOR_SYSTEM_DOLBYVISION,
            .levels=PL_COLOR_LEVELS_FULL,.dovi=&dv};
        pl_shader sh = pl_shader_alloc(NULL, pl_shader_params(.id=217,
            .glsl={.version=300,.gles=true},.dynamic_constants=true));
        pl_shader_decode_color(sh,&repr,NULL);
        const struct pl_shader_res *res = pl_shader_finalize(sh);
        assert(res);
        struct gl_shader_cache sc = {0};
        assert(aurora_dovi_emit_shader(&sc,res));
        assert(strstr(sc.header,"pl_shader_reshape"));
        assert(sc.count > 20);
        char path[1024];snprintf(path,sizeof(path),"%s/%s.frag",argv[1],mmr==2?"dovi-full-mmr":mmr?"dovi-mmr":"dovi-poly");
        FILE *out=fopen(path,"w");assert(out);
        fprintf(out,"#version 300 es\nprecision highp float;\nprecision highp int;\n%s\n%s\nout vec4 frag;\nvoid main(){vec4 color=vec4(0.25,0.5,0.5,1.0);\n%s\nfrag=color;}\n",sc.uniforms,sc.header,sc.body);
        fclose(out);
        printf("%s: uniforms=%d, descriptors=%d, constants=%d\n",path,sc.count,res->num_descriptors,res->num_constants);
        pl_shader_free(&sh);
        free(sc.uniforms);free(sc.header);free(sc.body);
    }
    return 0;
}
