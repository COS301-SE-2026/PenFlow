from importlib.metadata import distribution

package = distribution("python-Wappalyzer")

if package.version != "0.3.1":
    raise RuntimeError(
        "Review the Wappalyzer compatibility patch for this version"
    )

path = package.locate_file("Wappalyzer/Wappalyzer.py")
source = path.read_text(encoding="utf-8")

old_import = "import pkg_resources"
new_import = "from importlib.resources import files"

old_read = (
    'pkg_resources.resource_string(__name__, "data/technologies.json")'
)
new_read = (
    'files("Wappalyzer").joinpath("data/technologies.json").read_bytes()'
)

if old_import in source:
    if source.count(old_import) != 1 or source.count(old_read) != 1:
        raise RuntimeError(
            "Unexpected Wappalyzer source; refusing patch"
        )

    path.write_text(
        source.replace(old_import, new_import).replace(
            old_read,
            new_read,
        ),
        encoding="utf-8",
    )

elif new_import not in source or new_read not in source:
    raise RuntimeError(
        "Unexpected Wappalyzer source; refusing patch"
    )

print("Wappalyzer resource-loading compatibility patch applied")