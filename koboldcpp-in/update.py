#!/bin/python

import sys
import requests
import hashlib
import os
import shutil
import subprocess
import argparse


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
        sys.stderr.print(f"Request error: {e}")
        return None


def update(args, pkginfo: PkgInfo):
    DEST_DIR = os.path.join(SCRIPT_DIR_PATH, "..", pkginfo.pkgname)

    if not args.test and args.push_only:
        subprocess.run(["git", "push", "-u", "origin", "master"], cwd=DEST_DIR)
        return

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
            f"provides=(\n    {'\n    '.join([
                f'"{provide}"' for provide in pkginfo.provides
            ])}\n)",
        )
    else:
        pkgbuild_content = pkgbuild_content.replace(
            "\n@PKGPROVIDES@\n",
            "\n",
        )

    if len(pkginfo.conflicts) > 0:
        pkgbuild_content = pkgbuild_content.replace(
            "@PKGCONFLICTS@",
            f"conflicts=(\n    {'\n    '.join([
                f'"{conflict}"' for conflict in pkginfo.conflicts
            ])}\n)",
        )
    else:
        pkgbuild_content = pkgbuild_content.replace(
            "\n@PKGCONFLICTS@\n",
            "\n",
        )

    if args.print:
        print(f"#### START {pkginfo.pkgname} ####")
        print(pkgbuild_content)
        print(f"#### END {pkginfo.pkgname} ####\n")

    if not args.test:
        subprocess.run(["git", "pull"], cwd=DEST_DIR)
        subprocess.run(["git", "checkout", "master"], cwd=DEST_DIR)

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
            subprocess.run(["makepkg", "--printsrcinfo"],
                           cwd=DEST_DIR, stdout=f)

        if args.commit:
            subprocess.run(["git", "add", "."], cwd=DEST_DIR)

            if args.amend:
                if args.no_edit:
                    subprocess.run(["git", "commit", "--amend", "--no-edit"],
                                   cwd=DEST_DIR)
                elif args.message:
                    command = ["git", "commit", "--amend"]
                    for msg in args.message:
                        command.append("-m")
                        command.append(msg)

                    subprocess.run(command, cwd=DEST_DIR)
                else:
                    subprocess.run(
                        ["git", "commit", "--amend",
                         "-m", f"Bump v{pkginfo.pkgver}"],
                        cwd=DEST_DIR
                    )
            else:
                if args.message:
                    command = ["git", "commit"]
                    for msg in args.message:
                        command.append("-m")
                        command.append(msg)
                    subprocess.run(command, cwd=DEST_DIR)
                else:
                    subprocess.run(["git", "commit", "-m",
                                    f"Bump v{pkginfo.pkgver}"], cwd=DEST_DIR)

            if args.push:
                subprocess.run(["git", "push", "-u", "origin", "master"],
                               cwd=DEST_DIR)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='KoboldCpp PKGBUILD generator')
    parser.add_argument('version', type=str, nargs='?',
                        help="KoboldCpp version")
    parser.add_argument('-c', '--commit',
                        action='store_true', help="Commit change")
    parser.add_argument('-p', '--push',
                        action='store_true', help="Push change")
    parser.add_argument('--push-only',
                        action='store_true', help="Push only")
    parser.add_argument('-a', '--amend',
                        action='store_true', help="Amend commit")
    parser.add_argument('-n', '--no-edit',
                        action='store_true', help="No edit amend commit")
    parser.add_argument('-t', '--test',
                        action='store_true', help="Test run")
    parser.add_argument('--print',
                        action='store_true', help="Print output")
    parser.add_argument('-m', '--message',
                        action='append', type=str,
                        help="Append commit message(s)")

    args = parser.parse_args()

    pkgver: str = args.version
    checksum: str | None = None

    if not args.push_only:
        if not pkgver:
            sys.stderr.print("Missing version.")
            exit(1)

        checksum = calculate_checksum(
            f"https://github.com/LostRuins/koboldcpp/archive/refs/tags/v{pkgver}.tar.gz"
        )
        if not checksum:
            sys.stderr.print("Cannot create checksum.")
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
            ["LLAMA_CUBLAS", "LLAMA_ARCHES_CU12"],
            ["koboldcpp=$pkgver"],
            ["koboldcpp"],
        ),
        PkgInfo(
            "koboldcpp-cuda-portable",
            pkgver,
            checksum,
            "(with CUDA, portable build for old CPUs)",
            ["cuda"],
            ["LLAMA_CUBLAS", "LLAMA_ARCHES_CU12",
                "LLAMA_PORTABLE", "LLAMA_NOAVX2"],
            ["koboldcpp=$pkgver", "koboldcpp-cuda=$pkgver"],
            ["koboldcpp", "koboldcpp-cuda"],
        ),
        PkgInfo(
            "koboldcpp-hipblas",
            pkgver,
            checksum,
            "(with HIPBLAS, for ROCM)",
            ["hipblas"],
            ["LLAMA_HIPBLAS"],
            ["koboldcpp=$pkgver", "koboldcpp-rocm=$pkgver"],
            ["koboldcpp"],
        ),
        PkgInfo(
            "koboldcpp-hipblas-portable",
            pkgver,
            checksum,
            "(with HIPBLAS, for ROCM, portable build for old CPUs)",
            ["hipblas"],
            ["LLAMA_HIPBLAS", "LLAMA_PORTABLE", "LLAMA_NOAVX2"],
            ["koboldcpp=$pkgver", "koboldcpp-rocm=$pkgver"],
            ["koboldcpp", "koboldcpp-rocm"],
        ),
    ]
    for pkgbuild in pkgbuilds:
        update(args, pkgbuild)
