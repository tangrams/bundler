#!/usr/bin/env python

import os, sys, glob, yaml, zipfile, argparse
from urlparse import urljoin

# Append uniform textures
# - uniforms could reference a texture already loaded from textures: {} or could explicitly define a texture file

LAYER_KEY_WORDS = ['data', 'filter', 'visible', 'enabled']

def getUniformTexturePath(fileList, basePath, rootNode, uniformTextureStr):
    referenceTexturePath = ""
    explicitUniformTexturePath = ""
    if ('textures' in rootNode) and (uniformTextureStr in rootNode['textures']):
        referenceTexturePath = os.path.relpath(rootNode['textures'][ uniformTextureStr]['url'], basePath)
    explicitUniformTexturePath = os.path.relpath(uniformTextureStr, basePath)

    if (os.path.exists(explicitUniformTexturePath)):
        return explicitUniformTexturePath
    elif (os.path.exists(referenceTexturePath)):
        return referenceTexturePath
    return None

def addUniformTextureDependency(fileList, basePath, rootNode, styleName, uniformName):
    key = rootNode['styles'][styleName]['shaders']['uniforms'][uniformName]

    if isinstance(key, basestring):
        uniformTexture = getUniformTexturePath(fileList, basePath, rootNode, key)
        if uniformTexture:
            rootNode['styles'][styleName]['shaders']['uniforms'][uniformName] = uniformTexture
            fileList.append(uniformTexture)
    elif isinstance(key, list):
        index = 0
        for textureStr in key:
            if isinstance(textureStr, basestring):
                uniformTexture = getUniformTexturePath(fileList, basePath, rootNode, textureStr)
                if uniformTexture:
                    rootNode['styles'][styleName]['shaders']['uniforms'][uniformName][index] = uniformTexture
                    fileList.append(uniformTexture)

def appendDrawRuleTexture(fileList, drawRule, basePath):
    if 'texture' in drawRule:
        drawRule['texture'] = os.path.relpath(drawRule['texture'], basePath)
        fileList.append(drawRule['texture'])

def appendLayerDrawRuleTextures(fileList, layerNode, basePath):
    for key in layerNode:
        if key in LAYER_KEY_WORDS:
            # ignore these layer keys
            continue
        elif key == 'draw':
            drawNode = layerNode['draw']
            for drawRules in drawNode:
                appendDrawRuleTexture(fileList, drawNode[drawRules], basePath)
        else:
            subLayerNode = layerNode[key]
            appendLayerDrawRuleTextures(fileList, subLayerNode, basePath)

# Fetch all asset dependencies in the constructed rootNode
def fetchDependencies(fileList, rootNode, basePath):
    # Search for fonts urls
    if 'fonts' in rootNode:
        fontsNode = rootNode['fonts']
        for font in fontsNode:
            fontNode = fontsNode[font]
            # single face object
            if 'url' in fontNode and type(fontNode['url']) is str:
                fontNode['url'] = os.path.relpath(fontNode['url'], basePath)
                fileList.append(fontNode['url'])
            else:
                # multiple font face objects
                index = 0
                for face in fontNode:
                    if 'url' in face:
                        face['url'] = os.path.relpath(face['url'], basePath)
                        index = index + 1
                        fileList.append(face['url'])

    # Search for textures urls
    if 'textures' in rootNode:
        texturesNode = rootNode['textures']
        for texture in texturesNode:
            textureNode = texturesNode[texture]
            if 'url' in textureNode:
                textureNode['url'] = os.path.relpath(textureNode['url'], basePath)
                fileList.append(textureNode['url'])

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
                        addUniformTextureDependency(fileList, basePath, rootNode, style, uniform)
            if 'texture' in styleNode:
                styleNode['texture'] = os.path.relpath(styleNode['texture'], basePath)
                fileList.append(styleNode['texture'])
            if 'material' in styleNode:
                materialNode = styleNode['material']
                if (type(materialNode) is dict):
                    for prop in ['emission', 'ambient', 'diffuse', 'specular', 'normal']:
                        propNode = materialNode[prop]
                        if (type(propNode) is dict and 'texture' in propNode):
                            propNode['texture'] = os.path.relpath(propNode['texture'], basePath)
                            fileList.append(propNode['texture'])
            if 'draw' in styleNode:
                drawNode = styleNode['draw']
                appendDrawRuleTexture(fileList, drawNode, basePath)

    # search texture paths defined in draw rule groups
    if 'layers' in rootNode:
        layersNode = rootNode['layers']
        for layerNode in layersNode:
            appendLayerDrawRuleTextures(fileList, layersNode[layerNode], basePath)

def validFileToBundle(fileName):
    # we atleast know we need to ignore bundling any network url (todo: fetch yaml http urls and do not ignore these)
    if (fileName.startswith("http") and not fileName.endswith(".yaml")):
        return False
    return True

def loadYaml(filename):
    with open(filename, 'r') as yamlFile:
        return yaml.safe_load(yamlFile)

def collectAllImports(allImports):
    if (len(allImports) <= 0):
        return
    
    subImports = {}
    for fileName in allImports:
        yamlFile = allImports[fileName]
        if 'import' in yamlFile:
            importNode = yamlFile['import']
            if (type(importNode) is str):
                importPath = os.path.abspath(urljoin(fileName, importNode))
                subImports[importPath] = loadYaml(importPath)
            else:
                for imp in importNode:
                    importPath = os.path.abspath(urljoin(fileName, imp))
                    subImports[importPath] = loadYaml(importPath)
            collectAllImports(subImports)
    allImports.update(subImports)

def getSceneImports(filename):
    imports = []
    directory = os.path.dirname(filename)
    yamlFile = loadYaml(filename)
    if 'import' in yamlFile:
        importNode = yamlFile['import']
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
        resolvedPath = urljoin(basePath, input)
        if (os.path.exists(resolvedPath)):
            return resolvedPath
    return input

def resolveSceneTextureUrls(texturesNode, basePath):
    for texture in texturesNode:
        textureNode = texturesNode[texture]
        if 'url' in textureNode:
            textureNode['url'] = resolveGenericPath(textureNode['url'], basePath)

def resolveMaterialTextureUrls(materialNode, basePath):
    if (type(materialNode) is dict):
        for prop in ['emission', 'ambient', 'diffuse', 'specular', 'normal']:
            if (type(materialNode[prop]) is dict and 'texture' in materialNode[prop]):
                materialNode[prop]['texture'] = resolveGenericPath(materialNode[prop]['texture'], basePath)

def resolveShaderTextureUrls(shadersNode, basePath):
    if (type(shadersNode) is dict):
        if 'uniforms' in shadersNode:
            for uniform in shadersNode['uniforms']:
                if (type(shadersNode['uniforms'][uniform]) is str):
                    shadersNode['uniforms'][uniform] = resolveGenericPath(shadersNode['uniforms'][uniform], basePath)
                elif (type(shadersNode['uniforms'][uniform]) is list):
                    resolvedUniforms = []
                    for uni in shadersNode['uniforms'][uniform]:
                        if type(uni) is str:
                            resolvedUniforms.append(resolveGenericPath(uni, basePath))
                    if resolvedUniforms: # make sure to not modify non-texture uniforms
                        shadersNode['uniforms'][uniform] = resolvedUniforms

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
        if 'draw' in stylesNode[style]:
            drawNode = stylesNode[style]['draw']
            if 'texture' in drawNode:
                stylesNode[style]['draw]']['texture'] = resolveGenericPath(stylesNode[style]['draw]']['texture'], basePath)

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

def resolveLayersDrawTexture(layerNode, basePath):
    for key in layerNode:
        if key in LAYER_KEY_WORDS:
            # ignore these layer keys
            continue
        elif key == 'draw':
            drawNode = layerNode['draw']
            for drawRule in drawNode:
                drawRuleNode = drawNode[drawRule]
                if 'texture' in drawRuleNode:
                    drawRuleNode['texture'] = resolveGenericPath(drawRuleNode['texture'], basePath)
        else:
            subLayerNode = layerNode[key]
            resolveLayersDrawTexture(subLayerNode, basePath)


def resolveSceneUrls(yamlRoot, filename):
    basePath = filename
    if 'textures' in yamlRoot:
        resolveSceneTextureUrls(yamlRoot['textures'], basePath)
    if 'styles' in yamlRoot:
        resolveSceneStyleUrls(yamlRoot['styles'], basePath)
    if 'fonts' in yamlRoot:
        resolveSceneFontsUrl(yamlRoot['fonts'], basePath)
    if 'layers' in yamlRoot:
        layersNode = yamlRoot['layers']
        for layerNode in layersNode:
            resolveLayersDrawTexture(yamlRoot['layers'][layerNode], basePath)


def importSceneRecursive(yamlRoot, filename, allImports, importedScenes):
    if filename in importedScenes:
        return
    importedScenes.add(filename)
    sceneNode = allImports[filename]
    if ((sceneNode is None) or (type(sceneNode) is not dict)):
        return
    imports = getSceneImports(filename)
    sceneNode['import'] = None
    for importScene in imports:
        importFilename = os.path.abspath(urljoin(filename, importScene))
        importSceneRecursive(yamlRoot, importFilename, allImports, importedScenes)
    importedScenes.remove(filename)
    print "merging scene file to root: ", filename
    mergeMapFields(yamlRoot, sceneNode)
    resolveSceneUrls(yamlRoot, filename)

# ================================== Main functions
def bundler(filename, unifiedYaml):
    print filename, os.getcwd()

    zipFilename = os.path.splitext(filename)[0] + '.zip'
    allImports = {}
    absFilename = os.path.abspath(filename)
    allImports[absFilename] = loadYaml(absFilename)
    collectAllImports(allImports)

    rootNode = {}
    importedScenes = set()
    importSceneRecursive(rootNode, absFilename, allImports, importedScenes)

    allDependencies = []
    basePath = os.path.dirname(absFilename)
    fetchDependencies(allDependencies, rootNode, basePath)

    if unifiedYaml:
        unifiedBundledSceneYamlPath = os.path.abspath(urljoin(absFilename, "./unifiedBundledScene.yaml"))
        with open(unifiedBundledSceneYamlPath, 'w') as outfile:
            yaml.dump(rootNode, outfile, default_flow_style=False)
        allDependencies.append(os.path.relpath(unifiedBundledSceneYamlPath, basePath))
    else:
        for file in allImports:
            allDependencies.append(os.path.relpath(file, basePath))

    files = list(set(allDependencies))
    print files

    print "Bundling ",filename,"width",len(files),"dependencies, into ",zipFilename
    zipf = zipfile.ZipFile(zipFilename, 'w', zipfile.ZIP_DEFLATED)
    for file in files:
        if (validFileToBundle(file) and os.path.exists(file)):
            zipf.write(file)
    zipf.close()

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("yamlFile", help = "root scene file to initiate bundling")
    parser.add_argument("-u", "--unified", action="store_true", help = "Create a unified yaml file post merging all imports, instead of nested import files")
    args = parser.parse_args()
    if args.unified:
        bundler(args.yamlFile, True)
    else:
        bundler(args.yamlFile, False)

if __name__ == "__main__":
    exit(main())
