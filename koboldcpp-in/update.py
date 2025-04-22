#!/bin/python

import sys
import requests
import hashlib
import os
import shutil
import subprocess


SCRIPT_DIR_PATH = os.path.dirname(os.path.realpath(__file__))


class PkgInfo:
    PKGDESC = "An easy-to-use AI text-generation software for GGML and GGUF models"
    PKGDEPS = ["python", "cblas", "clblast", "vulkan-icd-loader"]

    def __init__(
        self,
        pkgname: str,
        pkgver: str,
        pkgsum: str,
        extra_desc: str = "",
        extra_deps: list[str] = [],
        extra_build: list[str] = [],
        provides: list[str] = [],
        conflicts: list[str] = [],
    ):
        self.pkgname = pkgname
        self.pkgver = pkgver
        if extra_desc:
            self.pkgdesc = PkgInfo.PKGDESC + " " + extra_desc
        else:
            self.pkgdesc = PkgInfo.PKGDESC
        self.pkgdeps = PkgInfo.PKGDEPS + extra_deps
        self.pkgsum = pkgsum
        self.pkgbuildextra = extra_build
        self.provides = provides
        self.conflicts = conflicts


def calculate_checksum(url: str, hash=hashlib.sha256()):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

        for chunk in response.iter_content(chunk_size=8192):
            hash.update(chunk)

        return hash.hexdigest()
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return None


def update(pkginfo: PkgInfo):
    DEST_DIR = os.path.join(SCRIPT_DIR_PATH, "..", pkginfo.pkgname)

    pkgbuild_content = ""
    with open(
        os.path.join(SCRIPT_DIR_PATH, "PKGBUILD.in"),
        "r",
    ) as f:
        pkgbuild_content = f.read()

    pkgbuild_content = pkgbuild_content.replace("@PKGNAME@", pkginfo.pkgname)
    pkgbuild_content = pkgbuild_content.replace("@PKGVER@", pkginfo.pkgver)
    pkgbuild_content = pkgbuild_content.replace("@PKGDESC@", pkginfo.pkgdesc)
    pkgbuild_content = pkgbuild_content.replace("@PKGSUM@", pkginfo.pkgsum)
    pkgbuild_content = pkgbuild_content.replace(
        "@PKGDEPS@", "\n    ".join([f'"{dep}"' for dep in pkginfo.pkgdeps])
    )
    pkgbuild_content = pkgbuild_content.replace(
        "@PKGBUILDEXTRA@",
        " ".join([f"{extra}=1" for extra in pkginfo.pkgbuildextra]),
    )

    if len(pkginfo.provides) > 0:
        pkgbuild_content = pkgbuild_content.replace(
            "@PKGPROVIDES@",
            f"provides=(\n    {'\n    '.join([f'"{provide}"' for provide in pkginfo.provides])}\n)",
        )
    else:
        pkgbuild_content = pkgbuild_content.replace(
            "\n@PKGPROVIDES@\n",
            "\n",
        )

    if len(pkginfo.conflicts) > 0:
        pkgbuild_content = pkgbuild_content.replace(
            "@PKGCONFLICTS@",
            f"conflicts=(\n    {'\n    '.join([f'"{conflict}"' for conflict in pkginfo.conflicts])}\n)",
        )
    else:
        pkgbuild_content = pkgbuild_content.replace(
            "\n@PKGCONFLICTS@\n",
            "\n",
        )

    with open(os.path.join(DEST_DIR, "PKGBUILD"), "w") as f:
        f.write(pkgbuild_content)

    shutil.copyfile(
        os.path.join(SCRIPT_DIR_PATH, "koboldcpp.png"),
        os.path.join(DEST_DIR, "koboldcpp.png"),
    )
    shutil.copyfile(
        os.path.join(SCRIPT_DIR_PATH, "koboldcpp.desktop"),
        os.path.join(DEST_DIR, "koboldcpp.desktop"),
    )
    shutil.copyfile(
        os.path.join(SCRIPT_DIR_PATH, ".gitignore"),
        os.path.join(DEST_DIR, ".gitignore"),
    )

    with open(os.path.join(DEST_DIR, ".SRCINFO"), "w") as f:
        subprocess.run(["makepkg", "--printsrcinfo"], cwd=DEST_DIR, stdout=f)

    subprocess.run(["git", "add", "."], cwd=DEST_DIR)
    subprocess.run(["git", "commit", "-m", f"Bump v{pkginfo.pkgver}"], cwd=DEST_DIR)
    subprocess.run(["git", "push", "-u", "origin", "master"], cwd=DEST_DIR)


if __name__ == "__main__":
    pkgver = sys.argv[1]
    if not pkgver:
        print("Version is not set")
        exit(1)

    checksum = calculate_checksum(
        f"https://github.com/LostRuins/koboldcpp/archive/refs/tags/v{pkgver}.tar.gz"
    )
    if not checksum:
        print("Version not found")
        exit(1)

    pkgbuilds = [
        PkgInfo("koboldcpp", pkgver, checksum),
        PkgInfo(
            "koboldcpp-portable",
            pkgver,
            checksum,
            "(portable build for old CPUs)",
            [],
            ["LLAMA_PORTABLE", "LLAMA_NOAVX2"],
            ["koboldcpp=$pkgver"],
            ["koboldcpp"],
        ),
        PkgInfo(
            "koboldcpp-cuda",
            pkgver,
            checksum,
            "(with CUDA)",
            ["cuda"],
            ["LLAMA_CUBLAS"],
            ["koboldcpp=$pkgver"],
            ["koboldcpp"],
        ),
        PkgInfo(
            "koboldcpp-cuda-portable",
            pkgver,
            checksum,
            "(with CUDA, portable build for old CPUs)",
            ["cuda"],
            ["LLAMA_CUBLAS", "LLAMA_PORTABLE", "LLAMA_NOAVX2"],
            ["koboldcpp=$pkgver", "koboldcpp-cuda=$pkgver"],
            ["koboldcpp", "koboldcpp-cuda"],
        ),
    ]
    for pkgbuild in pkgbuilds:
        update(pkgbuild)
