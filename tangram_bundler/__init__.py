#!/usr/bin/env python

import os, sys, glob, yaml, zipfile

# Append yaml dependences in yaml_file ('import' files) to another yaml file (full_yaml_file)
def addDependencies(file_list, filename):
    file_list.append(os.path.normpath(filename))
    folder = os.path.dirname(filename)
    yaml_file = yaml.safe_load(open(filename))

    # TODO:
    #   - Check if any url actually exist and is local before doing nothing

    # Search for fonts urls
    if 'fonts' in yaml_file:
        for font in yaml_file['fonts']:
            # initial Tangram font support
            if 'url' in yaml_file['fonts'][font]:
                file_list.append(os.path.normpath(folder + '/' + yaml_file['fonts'][font]['url']))

            # newer Tangram font support
            for weight in yaml_file['fonts'][font]:
                if 'url' in weight:
                    file_list.append(os.path.normpath(folder + '/' + weight['url']))

    # Search for textures urls
    if 'textures' in yaml_file:
        for font in yaml_file['textures']:
            if 'url' in yaml_file['textures'][font]:
                file_list.append(os.path.normpath(folder + '/' + yaml_file['textures'][font]['url']))

    # Search for u_envmap urls
    if 'styles' in yaml_file:
        for style in yaml_file['styles']:
            if 'shaders' in yaml_file['styles'][style]:
                if 'uniforms' in yaml_file['styles'][style]['shaders']:
                    if 'u_envmap' in yaml_file['styles'][style]['shaders']['uniforms']:
                        file_list.append(os.path.normpath(folder + '/' + yaml_file['styles'][style]['shaders']['uniforms']['u_envmap']))

# styles:
#     building-grid:
#         base: polygons
#         lighting: false
#         mix: [hsv, scale-buildings]
#         texcoords: true
#         shaders:
#             uniforms:
#                 u_tex_grid: building-grid
#             defines:
#                 WALL_TINT: vec3(0.950, 0.950, 0.950)
#             blocks:
#                 color: |
#                     if (dot(vec3(0., 0., 1.), worldNormal()) < 1.0 - TANGRAM_EPSILON) {
#                         // If it's a wall
#                         color.rgb = hsv2rgb(rgb2hsv(color.rgb) * WALL_TINT);
#                         color.rgb = mix(color.rgb, vec3(0.),
#                                         texture2D(u_tex_grid, v_texcoord).a);
#                     }
#     terrain:
#         base: polygons
#         lighting: false
#         raster: normal
#         shaders:
#             uniforms:
#                 u_envmap: images/draw-test9.jpg


    # Search for inner dependemcies
    if 'import' in yaml_file:
        if (type(yaml_file['import']) is str):
            addDependencies(file_list, folder + '/' + yaml_file['import'])
        else:
            for file in yaml_file['import']:
                addDependencies(file_list, folder + '/' + file)

# ================================== Main functions
def bundler(full_filename):
    print full_filename, os.getcwd()
    filename, file_extension = os.path.splitext(full_filename)
    if file_extension == '.yaml':
        all_dependencies = []
        addDependencies(all_dependencies, './'+full_filename)
        files = list(set(all_dependencies))

        print "Bundling ",filename,"width",len(files),"dependencies, into ",filename+".zip"
        zipf = zipfile.ZipFile(filename+'.zip', 'w', zipfile.ZIP_DEFLATED)
        for file in files:
            zipf.write(file)
        zipf.close()
    else:
        print 'Error: file',

def main():
    if len(sys.argv) > 1:
        bundler(sys.argv[1])
    else:
        bundler(raw_input("What Tangram YAML scene file do you want to bundle into a zipfile?: "))

if __name__ == "__main__":
    exit(main())
