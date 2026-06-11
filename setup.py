import os
import re

from setuptools import setup

HERE = os.path.abspath(os.path.dirname(__file__))

# Path fragments that are excluded from the wheel.
# three.js ships docs/examples/manual that are not needed at runtime.
# static/description contains large GIFs/PNGs only used by the Odoo app store.
EXCLUDE_DIR_FRAGMENTS = [
    os.path.join("three.js", "manual"),
    os.path.join("three.js", "examples"),
    os.path.join("three.js", "test"),
    os.path.join("three.js", "docs"),
    os.path.join("three.js", "editor"),
    os.path.join("three.js", "utils"),
    os.path.join("three.js", "src"),
    os.path.join("three.js", "files"),
    os.path.join("static", "description"),
]

ASSET_EXTENSIONS = {
    ".xml", ".csv", ".po", ".pot",
    ".png", ".gif", ".jpg", ".jpeg", ".svg", ".ico",
    ".scss", ".css", ".js", ".ts", ".html", ".json",
    ".ttf", ".woff", ".woff2", ".eot", ".map",
}


def get_version():
    manifest = os.path.join(HERE, "plm", "__manifest__.py")
    with open(manifest) as f:
        content = f.read()
    match = re.search(r'"version"\s*:\s*"([^"]+)"', content)
    return match.group(1)


def get_addons():
    addons = []
    for item in sorted(os.listdir(HERE)):
        path = os.path.join(HERE, item)
        if (
            os.path.isdir(path)
            and os.path.exists(os.path.join(path, "__manifest__.py"))
            and not item.startswith(".")
        ):
            addons.append(item)
    return addons


def _is_excluded(abs_path):
    for fragment in EXCLUDE_DIR_FRAGMENTS:
        if fragment in abs_path:
            return True
    return False


def build_package_info(addons):
    packages = []
    package_dir = {}
    package_data = {}

    for addon in addons:
        addon_abs = os.path.join(HERE, addon)
        root_pkg = "odoo.addons.{}".format(addon)

        # Register all Python sub-packages (dirs with __init__.py)
        for root, dirs, files in os.walk(addon_abs):
            dirs[:] = sorted(
                d for d in dirs if not d.startswith(".") and d != "__pycache__"
            )
            rel_from_addon = os.path.relpath(root, addon_abs)
            rel_from_repo = os.path.relpath(root, HERE)

            if rel_from_addon == ".":
                pkg = root_pkg
            elif "__init__.py" not in files:
                continue
            else:
                pkg = "odoo.addons.{}.{}".format(
                    addon, rel_from_addon.replace(os.sep, ".")
                )
            packages.append(pkg)
            package_dir[pkg] = rel_from_repo

        # Collect all asset files for this addon, attached to the root package.
        # Paths are relative to the addon root directory.
        assets = []
        for root, dirs, files in os.walk(addon_abs):
            dirs[:] = sorted(
                d for d in dirs if not d.startswith(".") and d != "__pycache__"
            )
            if _is_excluded(root):
                dirs.clear()
                continue
            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                if ext in ASSET_EXTENSIONS:
                    rel = os.path.relpath(os.path.join(root, fname), addon_abs)
                    assets.append(rel)

        if assets:
            package_data[root_pkg] = assets

    return packages, package_dir, package_data


addons = get_addons()
packages, package_dir, package_data = build_package_info(addons)

setup(
    name="odooplm",
    version=get_version(),
    description="OdooPLM — Product Lifecycle Management suite for Odoo 18",
    long_description=open(os.path.join(HERE, "README.md")).read(),
    long_description_content_type="text/markdown",
    author="OmniaSolutions",
    author_email="info@omniasolutions.eu",
    url="https://odooplm.omniasolutions.website",
    project_urls={
        "Source": "https://github.com/OmniaGit/odooplm",
        "Documentation": "https://odooplm.omniasolutions.website",
        "Bug Tracker": "https://github.com/OmniaGit/odooplm/issues",
    },
    license="LGPL-3",
    classifiers=[
        "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
        "Programming Language :: Python :: 3",
        "Framework :: Odoo :: 18.0",
        "Topic :: Office/Business",
        "Intended Audience :: Manufacturing",
    ],
    python_requires=">=3.10",
    install_requires=[
        "odoo>=18.0,<19.0",
    ],
    extras_require={
        "cad": ["ezdxf", "matplotlib", "numpy-stl", "base64io", "to-3mf"],
        "3d": ["cadquery"],
        "full": ["ezdxf", "matplotlib", "numpy-stl", "base64io", "to-3mf", "cadquery"],
    },
    packages=packages,
    package_dir=package_dir,
    package_data=package_data,
    include_package_data=False,
)
