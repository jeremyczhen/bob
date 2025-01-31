# Bob build tool
# Copyright (C) 2019  Jan Klötzke
#
# SPDX-License-Identifier: GPL-3.0-or-later

from .common import CommonIDEGenerator
from pathlib import Path, PureWindowsPath
from pipes import quote
from uuid import UUID
from uuid import uuid4 as randomUuid
from uuid import uuid5 as sha1NsUuid
from xml.etree import ElementTree
import os
import sys

SOLUTION_TEMPLATE = """\

Microsoft Visual Studio Solution File, Format Version 12.00
# Visual Studio Version 16
VisualStudioVersion = 16.0.28803.352
MinimumVisualStudioVersion = 10.0.40219.1
{PROJECTS_LIST}
Global
	GlobalSection(SolutionConfigurationPlatforms) = preSolution
		Build|x86 = Build|x86
		Checkout+Build|x86 = Checkout+Build|x86
	EndGlobalSection
	GlobalSection(ProjectConfigurationPlatforms) = postSolution
{PROJECTS_CFG}
	EndGlobalSection
	GlobalSection(SolutionProperties) = preSolution
		HideSolutionNode = FALSE
	EndGlobalSection
	GlobalSection(ExtensibilityGlobals) = postSolution
		SolutionGuid = {{{SOLUTION_GUID}}}
	EndGlobalSection
EndGlobal
"""

SOLUTION_PROJECT_TEMPLATE = """\
Project("{{8BC9CEB8-8B4A-11D0-8D11-00A0C91BC942}}") = "{NAME}", "{NAME}\\{NAME}.vcxproj", "{{{GUID}}}"
EndProject"""

PROJECT_TEMPLATE = """\
<?xml version="1.0" encoding="utf-8"?>
<Project DefaultTargets="Build" xmlns="http://schemas.microsoft.com/developer/msbuild/2003">
  <ItemGroup Label="ProjectConfigurations">
    <ProjectConfiguration Include="Build|Win32">
      <Configuration>Build</Configuration>
      <Platform>Win32</Platform>
    </ProjectConfiguration>
    <ProjectConfiguration Include="Checkout+Build|Win32">
      <Configuration>Checkout+Build</Configuration>
      <Platform>Win32</Platform>
    </ProjectConfiguration>
  </ItemGroup>
  <PropertyGroup Label="Globals">
    <VCProjectVersion>16.0</VCProjectVersion>
    <ProjectGuid>{{{PROJECT_GUID}}}</ProjectGuid>
    <Keyword>Win32Proj</Keyword>
  </PropertyGroup>
  <Import Project="$(VCTargetsPath)\Microsoft.Cpp.Default.props" />
  <PropertyGroup Condition="'$(Configuration)|$(Platform)'=='Build|Win32'" Label="Configuration">
    <ConfigurationType>Makefile</ConfigurationType>
    <UseDebugLibraries>true</UseDebugLibraries>
    <PlatformToolset>v142</PlatformToolset>
  </PropertyGroup>
  <PropertyGroup Condition="'$(Configuration)|$(Platform)'=='Checkout+Build|Win32'" Label="Configuration">
    <ConfigurationType>Makefile</ConfigurationType>
    <UseDebugLibraries>true</UseDebugLibraries>
    <PlatformToolset>v142</PlatformToolset>
  </PropertyGroup>
  <Import Project="$(VCTargetsPath)\Microsoft.Cpp.props" />
  <ImportGroup Label="ExtensionSettings">
  </ImportGroup>
  <ImportGroup Label="Shared">
  </ImportGroup>
  <ImportGroup Label="PropertySheets" Condition="'$(Configuration)|$(Platform)'=='Build|Win32'">
    <Import Project="$(UserRootDir)\Microsoft.Cpp.$(Platform).user.props" Condition="exists('$(UserRootDir)\Microsoft.Cpp.$(Platform).user.props')" Label="LocalAppDataPlatform" />
  </ImportGroup>
  <ImportGroup Label="PropertySheets" Condition="'$(Configuration)|$(Platform)'=='Checkout+Build|Win32'">
    <Import Project="$(UserRootDir)\Microsoft.Cpp.$(Platform).user.props" Condition="exists('$(UserRootDir)\Microsoft.Cpp.$(Platform).user.props')" Label="LocalAppDataPlatform" />
  </ImportGroup>
  <PropertyGroup Label="UserMacros" />
  <ItemDefinitionGroup>
  </ItemDefinitionGroup>
  <Import Project="$(VCTargetsPath)\Microsoft.Cpp.targets" />
  <ImportGroup Label="ExtensionTargets">
  </ImportGroup>
{EXTENSIONS}
</Project>
"""

FILTERS_SOURCES_UUID = UUID("4FC737F1-C7A5-4376-A066-2A32D752A2FF")
FILTERS_HEADERS_UUID = UUID("93995380-89BD-4b04-88EB-625FBE52EBFB")
FILTERS_RESOURCES_UUID = UUID("67DA6AB6-F800-4c08-8B7A-83BB121AAD01")

FILTERS_TEMPLATE = """\
<?xml version="1.0" encoding="utf-8"?>
<Project ToolsVersion="4.0" xmlns="http://schemas.microsoft.com/developer/msbuild/2003">
  <ItemGroup>
    <Filter Include="Source Files">
      <UniqueIdentifier>{{4FC737F1-C7A5-4376-A066-2A32D752A2FF}}</UniqueIdentifier>
      <Extensions>cpp;c;cxx;def;odl;idl;hpj;bat;asm;asmx</Extensions>
    </Filter>
    <Filter Include="Header Files">
      <UniqueIdentifier>{{93995380-89BD-4b04-88EB-625FBE52EBFB}}</UniqueIdentifier>
      <Extensions>h;hpp;hxx;hm;inl;inc;xsd</Extensions>
    </Filter>
    <Filter Include="Resource Files">
      <UniqueIdentifier>{{67DA6AB6-F800-4c08-8B7A-83BB121AAD01}}</UniqueIdentifier>
      <Extensions>rc;ico;cur;bmp;dlg;rc2;rct;bin;rgs;gif;jpg;jpeg;jpe;resx</Extensions>
    </Filter>
{FILTERS}
  </ItemGroup>
{ITEMS}
</Project>
"""

#def relpath(pathFrom, pathTo):
#    if pathTo.is_absolute():
#        return str(pathTo)
#
#    if pathFrom.is_absolute():
#        ret = [ pathFrom.drive ]
#        pathFrom = list(pathFrom.parts)[1:]
#    else:
#        ret = []
#        pathFrom = list(pathFrom.parts)
#    pathTo = list(pathTo.parts)
#
#    while pathFrom and not 
#
#    return 

class Project:
    def __init__(self, recipesRoot, uuid, scan):
        self.uuid = uuid
        self.isRoot = scan.isRoot
        self.packagePath = scan.stack
        self.workspacePath = recipesRoot.joinpath(PureWindowsPath(scan.workspacePath))
        self.headers =   [ recipesRoot.joinpath(PureWindowsPath(i)) for i in scan.headers   ]
        self.sources =   [ recipesRoot.joinpath(PureWindowsPath(i)) for i in scan.sources   ]
        self.resources = [ recipesRoot.joinpath(PureWindowsPath(i)) for i in scan.resources ]
        self.incPaths =  [ recipesRoot.joinpath(PureWindowsPath(i)) for i in scan.incPaths  ]
        self.dependencies = scan.dependencies

    def generateProject(self, projects, cmd):
        items = []
        if self.headers:
            g = ElementTree.Element("ItemGroup")
            for i in self.headers: ElementTree.SubElement(g, "ClInclude", {"Include" : str(i)})
            items.append(ElementTree.tostring(g, encoding="unicode"))
        if self.sources:
            g = ElementTree.Element("ItemGroup")
            for i in self.sources: ElementTree.SubElement(g, "ClCompile", {"Include" : str(i)})
            items.append(ElementTree.tostring(g, encoding="unicode"))
        if self.resources:
            g = ElementTree.ElementTree("ItemGroup")
            for i in self.resources: ElementTree.SubElement(g, "Text", {"Include" : str(i)})
            items.append(ElementTree.tostring(g, encoding="unicode"))
        incPaths = []
        if self.dependencies:
            g = ElementTree.Element("ItemGroup")
            for i in sorted(self.dependencies):
                dep = ElementTree.SubElement(g, "ProjectReference",
                        {"Include" : "..\\{NAME}\\{NAME}.vcxproj".format(NAME=i)})
                ElementTree.SubElement(dep, "Project").text = "{" + str(projects[i].uuid) + "}"
                ElementTree.SubElement(dep, "LinkLibraryDependencies").text = "true"
                incPaths.extend(str(i) for i in projects[i].incPaths)

            items.append(ElementTree.tostring(g, encoding="unicode"))

        n = ElementTree.Element("PropertyGroup", {"Condition" : "'$(Configuration)|$(Platform)'=='Build|Win32'"})
        ElementTree.SubElement(n, "NMakeOutput")
        ElementTree.SubElement(n, "NMakeIncludeSearchPath").text = ";".join(incPaths)
        ElementTree.SubElement(n, "NMakeBuildCommandLine").text = cmd + " -v -b " + self.packagePath
        ElementTree.SubElement(n, "NMakeReBuildCommandLine").text = cmd + " -v -b -f --clean " + self.packagePath
        # TODO: NMakeCleanCommandLine == "rm -rf dev/{build,dist}"?
        items.append(ElementTree.tostring(n, encoding="unicode"))

        n = ElementTree.Element("PropertyGroup", {"Condition" : "'$(Configuration)|$(Platform)'=='Checkout+Build|Win32'"})
        ElementTree.SubElement(n, "NMakeOutput")
        ElementTree.SubElement(n, "NMakeIncludeSearchPath").text = ";".join(incPaths)
        ElementTree.SubElement(n, "NMakeBuildCommandLine").text = cmd + " -v " + self.packagePath
        ElementTree.SubElement(n, "NMakeReBuildCommandLine").text = cmd + " -v -f --clean " + self.packagePath
        # TODO: NMakeCleanCommandLine == "rm -rf dev/{build,dist}"?
        items.append(ElementTree.tostring(n, encoding="unicode"))

        return PROJECT_TEMPLATE.format(PROJECT_GUID=str(self.uuid),
                EXTENSIONS="\n".join(items))

    def generateFilters(self):
        items = []
        filters = {}

        def makeFilter(category, uuid, filePath):
            trail = [ category ]
            for i in filePath.relative_to(self.workspacePath).parent.parts:
                uuid = sha1NsUuid(uuid, i)
                trail.append(i)
                name = "\\".join(trail)
                if name not in filters:
                    f = ElementTree.Element("Filter", {"Include" : name})
                    ElementTree.SubElement(f, "UniqueIdentifier").text = "{" + str(uuid) + "}"
                    filters[name] = ElementTree.tostring(f, encoding="unicode")

            return "\\".join(trail)

        if self.headers:
            g = ElementTree.Element("ItemGroup")
            for i in self.headers:
                s = ElementTree.SubElement(g, "ClInclude", {"Include" : str(i)})
                ElementTree.SubElement(s, "Filter").text = makeFilter("Header Files", FILTERS_HEADERS_UUID, i)
            items.append(ElementTree.tostring(g, encoding="unicode"))
        if self.sources:
            g = ElementTree.Element("ItemGroup")
            for i in self.sources:
                s = ElementTree.SubElement(g, "ClCompile", {"Include" : str(i)})
                ElementTree.SubElement(s, "Filter").text = makeFilter("Source Files", FILTERS_SOURCES_UUID, i)
            items.append(ElementTree.tostring(g, encoding="unicode"))
        if self.resources:
            g = ElementTree.Element("ItemGroup")
            for i in self.resources:
                s = ElementTree.SubElement(g, "Text", {"Include" : str(i)})
                ElementTree.SubElement(s, "Filter").text = makeFilter("Resource Files", FILTERS_RESOURCES_UUID, i)
            items.append(ElementTree.tostring(g, encoding="unicode"))

        return FILTERS_TEMPLATE.format(FILTERS="\n".join(f for n,f in sorted(filters.items())),
                                       ITEMS="\n".join(items))


class Vs2019Generator(CommonIDEGenerator):
    def __init__(self):
        super().__init__("vs2019", "Generate Visual Studio 2019 solution")
        self.parser.add_argument('--uuid', help="Set solution UUID")

    def configure(self, package, argv):
        super().configure(package, argv)
        if self.args.uuid:
            self.uuid = UUID(self.args.uuid)
        else:
            self.uuid = randomUuid()

    def generate(self, extra):
        super().generate()
        extra = " ".join(quote(e) for e in extra)

        # gather root paths
        bobPwd = Path(os.getcwd())
        if sys.platform == 'msys':
            if os.getenv('WD') is None:
                raise BuildError("Cannot create Visual Studio project for Windows! MSYS2 must be started by msys2_shell.cmd script!")
            msysRoot = PureWindowsPath(os.getenv('WD')) / '..' / '..'
            winPwd = PureWindowsPath(os.popen('pwd -W').read().strip())
            winDestination = PureWindowsPath(os.popen('cygpath -w {}'.format(quote(self.destination))).read().strip())
            baseBuildMe = str(msysRoot / "msys2_shell.cmd") + \
                    " -msys2 -defterm -no-start -use-full-path -where " + \
                    str(winPwd)
            buildMe = os.path.join(self.destination, "buildme.sh")
            buildMeCmd = baseBuildMe + " " + buildMe
        else:
            winPwd = bobPwd
            winDestination = Path(self.destination)
            buildMe = os.path.join(self.destination, "buildme.cmd")
            buildMeCmd = buildMe

        projects = {
            name : Project(winPwd, sha1NsUuid(self.uuid, name), scan)
            for name,scan in self.packages.items()
        }

        if not self.args.update:
            self.updateFile(buildMe, self.__generateBuildme(extra))

        solutionProjectList = []
        solutionProjectConfigs = []
        for name,project in projects.items():
            p = os.path.join(self.destination, name)
            os.makedirs(p, exist_ok=True)
            self.updateFile(os.path.join(p, name+".vcxproj"), project.generateProject(projects, buildMeCmd),
                    encoding="utf-8", newline='\r\n')
            self.updateFile(os.path.join(p, name+".vcxproj.filters"), project.generateFilters(),
                    encoding="utf-8", newline='\r\n')

            solutionProjectList.append(SOLUTION_PROJECT_TEMPLATE.format(NAME=name, GUID=str(project.uuid).upper()))
            solutionProjectConfigs.append("\t\t{{{GUID}}}.Build|x86.ActiveCfg = Build|Win32".format(GUID=str(project.uuid).upper()))
            solutionProjectConfigs.append("\t\t{{{GUID}}}.Checkout+Build|x86.ActiveCfg = Checkout+Build|Win32".format(GUID=str(project.uuid).upper()))
            if project.isRoot:
                solutionProjectConfigs.append("\t\t{{{GUID}}}.Build|x86.Build.0 = Build|Win32".format(GUID=str(project.uuid).upper()))
                solutionProjectConfigs.append("\t\t{{{GUID}}}.Checkout+Build|x86.Build.0 = Checkout+Build|Win32".format(GUID=str(project.uuid).upper()))

        self.updateFile(os.path.join(self.destination, self.projectName+".sln"),
                SOLUTION_TEMPLATE.format(PROJECTS_LIST="\n".join(solutionProjectList),
                                         PROJECTS_CFG="\n".join(solutionProjectConfigs),
                                         SOLUTION_GUID=str(self.uuid)),
                encoding="utf-8", newline='\r\n')

    def __generateBuildme(self, extra):
        buildMe = []
        if sys.platform == 'msys':
            buildMe.append("#!/bin/sh")
            buildMe.append("export PATH=" + quote(os.environ["PATH"]))
        else:
            buildMe.append("@ECHO OFF")
        buildMe.append('bob dev "$@" ' + extra)
        projectCmd = "bob project -n " + extra + " vs2019 " + quote("/".join(self.rootPackage.getStack())) + \
            " -u --destination " + quote(self.destination) + ' --name ' + quote(self.projectName) + \
            " --uuid " + quote(str(self.uuid))
        # only add arguments which are relevant for .files or .includes. All other files are only modified if not build with
        # update only.
        for i in self.args.additional_includes:
            projectCmd += " -I " + quote(i)
        if self.args.filter:
            projectCmd += " --filter " + quote(self.args.filter)
        for e in self.args.excludes:
            projectCmd += " --exclude " + quote(e)
        for e in self.args.include:
            projectCmd += "--include " + quote(e)
        for e in self.args.start_includes:
            projectCmd += " -S " + quote(e)

        buildMe.append(projectCmd)
        return "\n".join(buildMe)


def vs2019ProjectGenerator(package, argv, extra):
    generator = Vs2019Generator()
    generator.configure(package, argv)
    generator.generate(extra)
