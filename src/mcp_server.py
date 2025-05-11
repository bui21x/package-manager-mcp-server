from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import subprocess
import json
import aiohttp
import os
import re
from packaging import version

app = FastAPI()

class PackageQuery(BaseModel):
    package_name: str
    package_manager: str = "pip"  # pip, npm, cargo, composer, etc.
    version: Optional[str] = None

class DependencyQuery(BaseModel):
    package_name: str
    package_manager: str = "pip"
    version: Optional[str] = None
    depth: Optional[int] = 1

class VersionQuery(BaseModel):
    package_name: str
    package_manager: str = "pip"
    version_constraint: Optional[str] = None

class PackageResult(BaseModel):
    package_name: str
    package_manager: str
    versions: List[str]
    latest_version: str
    description: Optional[str] = None
    error: Optional[str] = None

class DependencyResult(BaseModel):
    package_name: str
    package_manager: str
    dependencies: Dict
    error: Optional[str] = None

class VersionResult(BaseModel):
    package_name: str
    package_manager: str
    compatible_versions: List[str]
    recommended_version: Optional[str]
    error: Optional[str] = None

# Registry API URLs
PACKAGE_REGISTRIES = {
    "pip": "https://pypi.org/pypi/{package}/json",
    "npm": "https://registry.npmjs.org/{package}",
}

@app.post('/package_info', response_model=PackageResult)
async def get_package_info(query: PackageQuery):
    try:
        package_manager = query.package_manager.lower()
        
        if package_manager not in PACKAGE_REGISTRIES:
            return PackageResult(
                package_name=query.package_name,
                package_manager=package_manager,
                versions=[],
                latest_version="",
                error=f"Unsupported package manager: {package_manager}"
            )
        
        # Fetch package information from registry
        registry_url = PACKAGE_REGISTRIES[package_manager].format(package=query.package_name)
        async with aiohttp.ClientSession() as session:
            async with session.get(registry_url) as response:
                if response.status != 200:
                    return PackageResult(
                        package_name=query.package_name,
                        package_manager=package_manager,
                        versions=[],
                        latest_version="",
                        error=f"Package not found: {query.package_name}"
                    )
                
                data = await response.json()
        
        # Parse response based on package manager
        if package_manager == "pip":
            versions = list(data["releases"].keys())
            latest_version = data["info"]["version"]
            description = data["info"]["summary"]
        elif package_manager == "npm":
            versions = list(data["versions"].keys())
            latest_version = data["dist-tags"]["latest"]
            description = data["description"]
        else:
            versions = []
            latest_version = ""
            description = ""
        
        return PackageResult(
            package_name=query.package_name,
            package_manager=package_manager,
            versions=versions,
            latest_version=latest_version,
            description=description
        )
    except Exception as e:
        return PackageResult(
            package_name=query.package_name,
            package_manager=query.package_manager,
            versions=[],
            latest_version="",
            error=str(e)
        )

@app.post('/dependencies', response_model=DependencyResult)
async def get_dependencies(query: DependencyQuery):
    try:
        package_manager = query.package_manager.lower()
        
        if package_manager not in PACKAGE_REGISTRIES:
            return DependencyResult(
                package_name=query.package_name,
                package_manager=package_manager,
                dependencies={},
                error=f"Unsupported package manager: {package_manager}"
            )
        
        # Fetch package information from registry
        registry_url = PACKAGE_REGISTRIES[package_manager].format(package=query.package_name)
        async with aiohttp.ClientSession() as session:
            async with session.get(registry_url) as response:
                if response.status != 200:
                    return DependencyResult(
                        package_name=query.package_name,
                        package_manager=package_manager,
                        dependencies={},
                        error=f"Package not found: {query.package_name}"
                    )
                
                data = await response.json()
        
        # Extract dependencies based on package manager
        dependencies = {}
        if package_manager == "pip":
            version_to_check = query.version or data["info"]["version"]
            if version_to_check in data["releases"]:
                # Get dependencies from requires_dist
                requires_dist = data["info"].get("requires_dist", [])
                if requires_dist:
                    for dep in requires_dist:
                        # Parse dependency string
                        match = re.match(r"([^<>=~!]+)(.+)?", dep)
                        if match:
                            dep_name = match.group(1).strip()
                            dep_version = match.group(2) if match.group(2) else ""
                            dependencies[dep_name] = dep_version
        elif package_manager == "npm":
            version_to_check = query.version or data["dist-tags"]["latest"]
            if version_to_check in data["versions"]:
                # Get dependencies from package.json
                deps = data["versions"][version_to_check].get("dependencies", {})
                dependencies = deps
        
        return DependencyResult(
            package_name=query.package_name,
            package_manager=package_manager,
            dependencies=dependencies
        )
    except Exception as e:
        return DependencyResult(
            package_name=query.package_name,
            package_manager=query.package_manager,
            dependencies={},
            error=str(e)
        )

@app.post('/compatible_versions', response_model=VersionResult)
async def get_compatible_versions(query: VersionQuery):
    try:
        package_manager = query.package_manager.lower()
        
        if package_manager not in PACKAGE_REGISTRIES:
            return VersionResult(
                package_name=query.package_name,
                package_manager=package_manager,
                compatible_versions=[],
                error=f"Unsupported package manager: {package_manager}"
            )
        
        # Fetch package information from registry
        registry_url = PACKAGE_REGISTRIES[package_manager].format(package=query.package_name)
        async with aiohttp.ClientSession() as session:
            async with session.get(registry_url) as response:
                if response.status != 200:
                    return VersionResult(
                        package_name=query.package_name,
                        package_manager=package_manager,
                        compatible_versions=[],
                        error=f"Package not found: {query.package_name}"
                    )
                
                data = await response.json()
        
        # Get all versions
        all_versions = []
        if package_manager == "pip":
            all_versions = list(data["releases"].keys())
            latest_version = data["info"]["version"]
        elif package_manager == "npm":
            all_versions = list(data["versions"].keys())
            latest_version = data["dist-tags"]["latest"]
        
        # Filter compatible versions if version_constraint is provided
        compatible_versions = all_versions
        recommended_version = latest_version
        
        if query.version_constraint:
            constraint = query.version_constraint
            
            # Simple version constraint parsing
            if constraint.startswith(">="):
                min_version = constraint[2:].strip()
                compatible_versions = [v for v in all_versions if version.parse(v) >= version.parse(min_version)]
            elif constraint.startswith(">"):
                min_version = constraint[1:].strip()
                compatible_versions = [v for v in all_versions if version.parse(v) > version.parse(min_version)]
            elif constraint.startswith("<="):
                max_version = constraint[2:].strip()
                compatible_versions = [v for v in all_versions if version.parse(v) <= version.parse(max_version)]
            elif constraint.startswith("<"):
                max_version = constraint[1:].strip()
                compatible_versions = [v for v in all_versions if version.parse(v) < version.parse(max_version)]
            elif constraint.startswith("=="):
                exact_version = constraint[2:].strip()
                compatible_versions = [v for v in all_versions if v == exact_version]
            elif constraint.startswith("~="):
                compatible_version = constraint[2:].strip()
                # Approximate version matching
                parts = compatible_version.split(".")
                prefix = ".".join(parts[:-1]) + "."
                compatible_versions = [v for v in all_versions if v.startswith(prefix)]
            
            # Update recommended version
            if compatible_versions:
                compatible_versions.sort(key=lambda v: version.parse(v), reverse=True)
                recommended_version = compatible_versions[0]
            else:
                recommended_version = None
        
        return VersionResult(
            package_name=query.package_name,
            package_manager=package_manager,
            compatible_versions=compatible_versions,
            recommended_version=recommended_version
        )
    except Exception as e:
        return VersionResult(
            package_name=query.package_name,
            package_manager=query.package_manager,
            compatible_versions=[],
            error=str(e)
        )

@app.get('/supported_package_managers')
async def get_supported_package_managers():
    return {"supported_package_managers": list(PACKAGE_REGISTRIES.keys())}

@app.get('/health')
async def health_check():
    return {"status": "healthy"}