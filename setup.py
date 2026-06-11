import os
import re
from setuptools import setup

HERE = os.path.abspath(os.path.dirname(__file__))

# Recursive patterns for all non-Python addon assets (views, security, i18n,
# static files including git-submodule JS libraries with dots in dir names).
ASSET_PATTERNS = [
    "**/*.xml", "**/*.csv", "**/*.po", "**/*.pot",
    "**/*.png", "**/*.gif", "**/*.jpg", "**/*.jpeg", "**/*.svg", "**/*.ico",
    "**/*.scss", "**/*.css", "**/*.js", "**/*.ts", "**/*.html",
    "**/*.json", "**/*.ttf", "**/*.woff", "**/*.woff2", "**/*.eot", "**/*.map",
]


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


def build_package_info(addons):
    packages = []
    package_dir = {}
    for addon in addons:
        addon_path = os.path.join(HERE, addon)
        for root, dirs, files in os.walk(addon_path):
            dirs[:] = sorted(
                d for d in dirs if not d.startswith(".") and d != "__pycache__"
            )
            # Only register directories that are actual Python packages.
            # Non-Python asset trees (static/, views/, i18n/, etc.) are
            # covered by ASSET_PATTERNS in package_data on the addon root,
            # which preserves directory names with dots (e.g. three.js/).
            rel_from_addon = os.path.relpath(root, addon_path)
            if rel_from_addon != "." and "__init__.py" not in files:
                continue

            rel_from_repo = os.path.relpath(root, HERE)
            if rel_from_addon == ".":
                pkg = "odoo.addons.{}".format(addon)
            else:
                pkg = "odoo.addons.{}.{}".format(
                    addon, rel_from_addon.replace(os.sep, ".")
                )
            packages.append(pkg)
            package_dir[pkg] = rel_from_repo
    return packages, package_dir


addons = get_addons()
packages, package_dir = build_package_info(addons)

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
    package_data={pkg: ASSET_PATTERNS for pkg in packages},
    include_package_data=False,
)
