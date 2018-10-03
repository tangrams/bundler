#!/usr/bin/env python

import os, sys, glob, yaml, zipfile
from urlparse import urljoin

# Append uniform textures
# - uniforms could reference a texture already loaded from textures: {} or could explicitly define a texture file
def addUniformTextureDependency(file_list, basePath, rootNode, styleName, uniformName):
    referenceTexturePath = ""
    explicitUniformTexturePath = ""
    key = rootNode['styles'][styleName]['shaders']['uniforms'][uniformName]

    if isinstance(key, basestring):
        if ('textures' in rootNode) and (key in rootNode['textures']):
            referenceTexturePath = os.path.relpath(rootNode['textures'][ rootNode['styles'][styleName]['shaders']['uniforms'][uniformName] ]['url'], basePath)
        explicitUniformTexturePath = os.path.relpath(rootNode['styles'][styleName]['shaders']['uniforms'][uniformName], basePath)

    if (os.path.exists(explicitUniformTexturePath)):
        file_list.append(explicitUniformTexturePath)
    elif (os.path.exists(referenceTexturePath)):
        file_list.append(referenceTexturePath)


# Append yaml dependences in rootNode ('import' files) to another yaml file (full_rootNode)
def addDependencies(file_list, rootNode, basePath):
    # Search for fonts urls
    if 'fonts' in rootNode:
        fontsNode = rootNode['fonts']
        for font in fontsNode:
            fontNode = fontsNode[font]
            for prop in fontNode:
                # initial Tangram font support
                if 'url' in prop:
                    file_list.append(os.path.relpath(prop['url'], basePath))
                # newer Tangram font support
                if 'weight' in prop and type(prop['weight']) is str:
                    file_list.append(os.path.relpath(prop['weight'], basePath))

    # Search for textures urls
    if 'textures' in rootNode:
        texturesNode = rootNode['textures']
        for texture in texturesNode:
            textureNode = texturesNode[texture]
            if 'url' in textureNode:
                file_list.append(os.path.relpath(textureNode['url'], basePath))

    # Search for asset url in styles
    if 'styles' in rootNode:
        stylesNode = rootNode['styles']
        for style in stylesNode:
            styleNode = stylesNode[style]
            if 'shaders' in styleNode:
                shadersNode = styleNode['shaders']
                if 'uniforms' in shadersNode:
                    uniformsNode = shadersNode['uniforms']
                    for uniform in uniformsNode:
                        addUniformTextureDependency(file_list, basePath, rootNode, style, uniform)
            if 'texture' in styleNode:
                file_list.append(os.path.relpath(styleNode['texture'], basePath))
            if 'material' in styleNode:
                materialNode = styleNode['material']
                if (type(materialNode) is dict):
                    for prop in ['emission', 'ambient', 'diffuse', 'specular', 'normal']:
                        propNode = materialNode[prop]
                        if (type(propNode) is dict and 'texture' in propNode):
                            file_list.append(os.path.relpath(propNode['texture'], basePath))


def ignoreFileForBundling(fileName):
    # we atleast know we need to ignore bundling any network url (todo: fetch yaml http urls and do not ignore these)
    if (fileName.startswith("http") and not fileName.endswith(".yaml")):
        return False
    return True

def collectAllImports(all_imports):
    if (len(all_imports) <= 0):
        return
    
    subImports = {}
    for fileName in all_imports:
        yaml_file = all_imports[fileName]
        directory = os.path.dirname(fileName)
        if 'import' in yaml_file:
            importNode = yaml_file['import']
            if (type(importNode) is str):
                importPath = os.path.abspath(directory + '/' + importNode)
                subImports[importPath] = yaml.safe_load(open(importPath)) 
            else:
                for imp in importNode:
                    importPath = os.path.abspath(directory + '/' + imp)
                    subImports[importPath] = yaml.safe_load(open(importPath))
            collectAllImports(subImports)
    all_imports.update(subImports)

def getSceneImports(filename):
    imports = []
    directory = os.path.dirname(filename)
    yaml_file = yaml.safe_load(open(filename))
    if 'import' in yaml_file:
        importNode = yaml_file['import']
        if (type(importNode) is str):
            importPath = directory + '/' + importNode
            imports.append(importPath)
        else:
            for imp in importNode:
                importPath = directory + '/' + imp
                imports.append(importPath)
    return imports

def mergeMapFields(yamlRoot, sceneNode):
    for key in sceneNode:
        source = sceneNode[key]
        if key not in yamlRoot:
            yamlRoot[key] = source
            continue
        if ((yamlRoot[key] is None) or (type(yamlRoot[key]) is not dict)):
            yamlRoot[key] = source
        else: #(type(yamlRoot[key]) is dict):
            if (type(source) is dict):
                mergeMapFields(yamlRoot[key], source)
            else:
                yamlRoot[key] = source

def resolveGenericPath(input, basePath):
    if (type(input) is str):
        return urljoin(basePath, input)
    else:
        return input

def resolveSceneTextureUrls(texturesNode, basePath):
    for texture in texturesNode:
        textureNode = texturesNode[texture]
        if 'url' in textureNode:
            textureNode['url'] = resolveGenericPath(textureNode['url'], basePath)

def resolveMaterialTextureUrls(materialNode, basePath):
    if (type(materialNode) is dict):
        for prop in ['emission', 'ambient', 'diffuse', 'specular', 'normal']:
            propNode = materialNode[prop]
            if (type(materialNode[prop]) is dict and 'texture' in materialNode[prop]):
                materialNode[prop]['texture'] = resolveGenericPath(materialNode[prop]['texture'], basePath)

def resolveShaderTextureUrls(shadersNode, basePath):
    if (type(shadersNode) is dict):
        if 'uniforms' in shadersNode:
            for uniform in shadersNode['uniforms']:
                if (type(shadersNode['uniforms'][uniform]) is str):
                    shadersNode['uniforms'][uniform] = resolveGenericPath(shadersNode['uniforms'][uniform], basePath)
                elif (type(shadersNode['uniforms'][uniform]) is list):
                    for uni in shadersNode['uniforms'][uniform]:
                        if type(uni) is str:
                            uni = resolveGenericPath(shadersNode['uniforms'][uniform][uni], basePath)

def resolveSceneStyleUrls(stylesNode, basePath):
    for style in stylesNode:
        if (type(stylesNode[style]) is not dict):
            continue
        if 'texture' in stylesNode[style]:
            stylesNode[style]['texture'] = resolveGenericPath(stylesNode[style]['texture'], basePath)
        if 'material' in stylesNode[style]:
            resolveMaterialTextureUrls(stylesNode[style]['materials'], basePath)
        if 'shaders' in stylesNode[style]:
            resolveShaderTextureUrls(stylesNode[style]['shaders'], basePath)

def resolveSceneFontsUrl(fontsNode, basePath):
    if (type(fontsNode) is dict):
        for font in fontsNode:
            fontNode = fontsNode[font]
            if (type(fontNode) is dict and 'url' in fontNode):
                fontNode['url'] = resolveGenericPath(fontNode['url'], basePath)
            elif(type(fontNode) is list):
                for f in fontNode:
                    if 'url' in f:
                        f['url'] = resolveGenericPath(f['url'], basePath)

def resolveSceneUrls(yamlRoot, filename):
    basePath = filename
    if 'textures' in yamlRoot:
        resolveSceneTextureUrls(yamlRoot['textures'], basePath)
    if 'styles' in yamlRoot:
        resolveSceneStyleUrls(yamlRoot['styles'], basePath)
    if 'fonts' in yamlRoot:
        resolveSceneFontsUrl(yamlRoot['fonts'], basePath)


def importSceneRecursive(yamlRoot, filename, all_imports, importedScenes):
    if filename in importedScenes:
        return
    importedScenes.add(filename)
    sceneNode = all_imports[filename]
    if ((sceneNode is None) or (type(sceneNode) is not dict)):
        return
    imports = getSceneImports(filename)
    sceneNode['import'] = None
    for importScene in imports:
        importSceneRecursive(yamlRoot, importScene, all_imports, importedScenes)
    importedScenes.remove(filename)
    print "merging scene file to root: ", filename
    mergeMapFields(yamlRoot, sceneNode)
    resolveSceneUrls(yamlRoot, filename)

# ================================== Main functions
def bundler(full_filename):
    print full_filename, os.getcwd()
    filename, file_extension = os.path.splitext(full_filename)
    if file_extension == '.yaml':

        all_imports = {}
        absFilename = os.path.abspath(full_filename)
        all_imports[absFilename]= yaml.safe_load(open(absFilename))
        collectAllImports(all_imports)
        
        rootNode = {}
        importedScenes = set()
        importSceneRecursive(rootNode, absFilename, all_imports, importedScenes)

        all_dependencies = []
        basePath = os.path.dirname(absFilename)
        addDependencies(all_dependencies, rootNode, basePath)

        for file in all_imports:
            all_dependencies.append(os.path.relpath(file, basePath))

        files = list(set(all_dependencies))
        print files

        print "Bundling ",filename,"width",len(files),"dependencies, into ",filename+".zip"
        zipf = zipfile.ZipFile(filename+'.zip', 'w', zipfile.ZIP_DEFLATED)
        for file in files:
            if (ignoreFileForBundling(file) and os.path.exists(file)):
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
