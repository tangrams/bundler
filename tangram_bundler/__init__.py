#!/usr/bin/env python

import os, sys, glob, yaml, zipfile

# Append uniform textures
# - uniforms could reference a texture already loaded from textures: {} or could explicitly define a texture file
def addUniformTextureDependency(file_list, basePath, yaml_file, styleName, uniformName):
    referenceTexturePath = ""
    explicitUniformTexturePath = ""
    key = yaml_file['styles'][styleName]['shaders']['uniforms'][uniformName]

    if isinstance(key, basestring):
        if ('textures' in yaml_file) and (key in yaml_file['textures']):
            referenceTexturePath = basePath + '/' + yaml_file['textures'][ yaml_file['styles'][styleName]['shaders']['uniforms'][uniformName] ]['url']
        explicitUniformTexturePath = basePath + '/' + yaml_file['styles'][styleName]['shaders']['uniforms'][uniformName]

    if (os.path.exists(explicitUniformTexturePath)):
        file_list.append(os.path.normpath(explicitUniformTexturePath))
    elif (os.path.exists(referenceTexturePath)):
        file_list.append(os.path.normpath(referenceTexturePath))


# Append yaml dependences in yaml_file ('import' files) to another yaml file (full_yaml_file)
def addDependencies(file_list, filename):
    print "Adding dependencies for file: ", filename
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
        for texture in yaml_file['textures']:
            if 'url' in yaml_file['textures'][texture]:
                file_list.append(os.path.normpath(folder + '/' + yaml_file['textures'][texture]['url']))

    # Search for u_envmap or u_ramp urls
    if 'styles' in yaml_file:
        for style in yaml_file['styles']:
            if 'shaders' in yaml_file['styles'][style]:
                if 'uniforms' in yaml_file['styles'][style]['shaders']:
                    for uniform in yaml_file['styles'][style]['shaders']['uniforms']:
                        addUniformTextureDependency(file_list, folder, yaml_file, style, uniform)

    # Search for inner dependencies
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

        # 1st order dependencies
        addDependencies(all_dependencies, './'+full_filename)

        # 2nd order theme dependencies
        try:
            for file in os.listdir(os.getcwd() + "/themes"):
                if file.endswith(".yaml"):
                    # track like normal
                    all_dependencies.append("themes/" + file)
                    # some themes require additional assets
                    print "looking at dependencies for: %s" % (file,)
                    addDependencies(all_dependencies, "themes/" + file)
        except Exception:
            print "\tskipping: themes (none found)"

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
