import argparse
import glob
import os
import platform
import re
import shutil
import subprocess

from cibuildpkg import Builder, Package, When, fetch, get_platform, log_group, run

plat = platform.system()

def windows_openssl_root() -> str:
    r"""Where libsrt's CMake finds OpenSSL on Windows.

    Upstream hard-codes the runner's C:\Program Files\OpenSSL; the windows-2025 image still
    has that directory but no crypto library in it (CMake: "missing: OPENSSL_CRYPTO_LIBRARY").
    Raven: the MSYS2 mingw64 prefix that mingw-w64-x86_64-openssl installs into (OpenSSL 3,
    Apache-2.0), derived from the gcc on PATH, whenever it holds libcrypto; Program Files
    only as the historical fallback.
    """
    gcc = shutil.which("gcc")
    if gcc:
        prefix = os.path.dirname(os.path.dirname(gcc))
        if os.path.exists(os.path.join(prefix, "lib", "libcrypto.dll.a")):
            return prefix.replace("\\", "/")
    return r"C:\Program Files\OpenSSL"


library_group = [
    Package(
        name="xz",
        source_url="https://github.com/tukaani-project/xz/releases/download/v5.6.3/xz-5.6.3.tar.xz",
        build_arguments=[
            "--disable-doc",
            "--disable-lzma-links",
            "--disable-lzmadec",
            "--disable-lzmainfo",
            "--disable-nls",
            "--disable-scripts",
            "--disable-xz",
            "--disable-xzdec",
        ],
    ),
    Package(
        name="gmp",
        source_url="https://ftp.gnu.org/gnu/gmp/gmp-6.3.0.tar.xz",
        # out-of-tree builds fail on Windows
        build_dir=".",
    ),
    Package(
        name="xml2",
        requires=["xz"],
        source_url="https://download.gnome.org/sources/libxml2/2.9/libxml2-2.9.13.tar.xz",
        build_arguments=["--without-python"],
    ),
]

gnutls_group = [
    Package(
        name="unistring",
        source_url="https://ftp.gnu.org/gnu/libunistring/libunistring-1.2.tar.gz",
    ),
    Package(
        name="nettle",
        requires=["gmp"],
        source_url="https://ftp.gnu.org/gnu/nettle/nettle-3.9.1.tar.gz",
        build_arguments=["--disable-documentation"],
        # build randomly fails with "*** missing separator.  Stop."
        build_parallel=False,
    ),
    Package(
        name="gnutls",
        requires=["nettle", "unistring"],
        source_url="https://www.gnupg.org/ftp/gcrypt/gnutls/v3.8/gnutls-3.8.1.tar.xz",
        build_arguments=[
            "--disable-cxx",
            "--disable-doc",
            "--disable-guile",
            "--disable-libdane",
            "--disable-nls",
            "--disable-tests",
            "--disable-tools",
            "--with-included-libtasn1",
            "--without-p11-kit",
        ],
    ),
]

codec_group = [
    Package(
        name="aom",
        requires=["cmake"],
        source_url="https://storage.googleapis.com/aom-releases/libaom-3.11.0.tar.gz",
        source_strip_components=1,
        build_system="cmake",
        build_arguments=[
            "-DENABLE_DOCS=0",
            "-DENABLE_EXAMPLES=0",
            "-DENABLE_TESTS=0",
            "-DENABLE_TOOLS=0",
        ],
        build_parallel=False,
    ),
    Package(
        name="dav1d",
        requires=["meson", "nasm", "ninja"],
        # Raven: VideoLAN's release mirror instead of the GitLab archive endpoint, which served
        # the GitHub runners a corrupt archive on both platforms (sha256 published beside it:
        # 8d407dd5fe7986413c937b14e67f36aebd06e1fa5cfec679d10e548476f2d5f8).
        source_url="https://downloads.videolan.org/pub/videolan/dav1d/1.4.1/dav1d-1.4.1.tar.xz",
        build_system="meson",
    ),
    Package(
        name="libsvtav1",
        source_url="https://gitlab.com/AOMediaCodec/SVT-AV1/-/archive/v2.2.1/SVT-AV1-v2.2.1.tar.gz",
        build_system="cmake",
    ),
    Package(
        name="lame",
        source_url="http://deb.debian.org/debian/pool/main/l/lame/lame_3.100.orig.tar.gz",
    ),
    Package(
        name="ogg",
        source_url="http://downloads.xiph.org/releases/ogg/libogg-1.3.5.tar.gz",
    ),
    Package(
        name="opus",
        source_url="https://github.com/xiph/opus/releases/download/v1.5.2/opus-1.5.2.tar.gz",
        build_arguments=["--disable-doc", "--disable-extra-programs"],
    ),
    Package(
        name="speex",
        source_url="http://downloads.xiph.org/releases/speex/speex-1.2.1.tar.gz",
        build_arguments=["--disable-binaries"],
    ),
    Package(
        name="twolame",
        source_url="http://deb.debian.org/debian/pool/main/t/twolame/twolame_0.4.0.orig.tar.gz",
        build_arguments=["--disable-sndfile"],
    ),
    Package(
        name="vorbis",
        requires=["ogg"],
        source_url="http://downloads.xiph.org/releases/vorbis/libvorbis-1.3.7.tar.gz",
    ),
    Package(
        name="vpx",
        source_filename="vpx-1.14.0.tar.gz",
        source_url="https://github.com/webmproject/libvpx/archive/v1.14.0.tar.gz",
        build_arguments=[
            "--disable-examples",
            "--disable-tools",
            "--disable-unit-tests",
        ],
    ),
    Package(
        name="png",
        source_url="https://download.sourceforge.net/libpng/libpng-1.6.45.tar.gz",
        # avoid an assembler error on Windows
        build_arguments=["PNG_COPTS=-fno-asynchronous-unwind-tables"],
    ),
    Package(
        name="webp",
        source_filename="webp-1.5.0.tar.gz",
        source_url="https://github.com/webmproject/libwebp/archive/refs/tags/v1.5.0.tar.gz",
        build_system="cmake",
        build_arguments=[
            "-DWEBP_BUILD_ANIM_UTILS=OFF",
            "-DWEBP_BUILD_CWEBP=OFF",
            "-DWEBP_BUILD_DWEBP=OFF",
            "-DWEBP_BUILD_GIF2WEBP=OFF",
            "-DWEBP_BUILD_IMG2WEBP=OFF",
            "-DWEBP_BUILD_VWEBP=OFF",
            "-DWEBP_BUILD_WEBPINFO=OFF",
            "-DWEBP_BUILD_WEBPMUX=OFF",
            "-DWEBP_BUILD_BUILD_EXTRAS=OFF",
        ],
    ),
    Package(
        name="openh264",
        requires=["meson", "nasm", "ninja"],
        source_filename="openh264-2.5.0.tar.gz",
        source_url="https://github.com/cisco/openh264/archive/refs/tags/v2.5.0.tar.gz",
        build_system="meson",
        when=When.commercial_only,
    ),
    Package(
        name="fdk_aac",
        source_url="https://github.com/mstorsjo/fdk-aac/archive/refs/tags/v2.0.3.tar.gz",
        when=When.commercial_only,
        build_system="cmake",
    ),
    Package(
        name="opencore-amr",
        source_url="http://deb.debian.org/debian/pool/main/o/opencore-amr/opencore-amr_0.1.5.orig.tar.gz",
        # parallel build hangs on Windows
        build_parallel=plat != "Windows",
        when=When.community_only,
    ),
    Package(
        name="x264",
        source_url="https://code.videolan.org/videolan/x264/-/archive/master/x264-master.tar.bz2",
        # parallel build runs out of memory on Windows
        build_parallel=plat != "Windows",
        when=When.community_only,
    ),
    Package(
        name="x265",
        requires=["cmake"],
        source_url="https://bitbucket.org/multicoreware/x265_git/downloads/x265_3.5.tar.gz",
        build_system="cmake",
        source_dir="source",
        when=When.community_only,
    ),
    Package(
        name="srt",
        source_url="https://github.com/Haivision/srt/archive/refs/tags/v1.5.4.tar.gz",
        build_system="cmake",
        build_arguments=(
            ["-DOPENSSL_ROOT_DIR=" + windows_openssl_root()]
            if plat == "Windows"
            else ["-DENABLE_ENCRYPTION=OFF"]
            if plat == "Darwin"
            else [""]
        ),
        when=When.community_only,
    ),
]

nvheaders = Package(
    name="nv-codec-headers",
    source_url="https://github.com/FFmpeg/nv-codec-headers/archive/refs/tags/n13.0.19.0.tar.gz",
    build_system="make",
)

ffmpeg_package = Package(
    name="ffmpeg",
    source_url="https://ffmpeg.org/releases/ffmpeg-7.1.tar.xz",
    build_arguments=[],
    build_parallel=plat != "Windows",
)


# Raven (https://raven.video) --lgpl mode: the community build minus every package that would
# lift FFmpeg's license floor above LGPL-2.1-or-later. x264/x265 are GPL; gmp and the
# opencore-amr codecs pull in --enable-version3 (LGPL v3); openh264 and fdk_aac belong to the
# commercial variant. libsrt (MPL-2.0) stays: it is what the community build ships and Raven's
# SRT legs need it. gmp is still built on Linux, where gnutls's nettle requires it.
LGPL_EXCLUDED_PACKAGES = {"x264", "x265", "opencore-amr", "openh264", "fdk_aac"}

# Raven --gpl-child mode: the GPL encoder helper (Raven's docs/ffmpeg-gpl-lgpl-split-plan.md,
# FS16) -- an unmodified, STATIC `ffmpeg` executable carrying nothing but x264 and x265, the NUT
# demuxer/muxer, the rawvideo decoder and the pipe protocol. Raven runs it as a separate process
# fed over pipes, so it must not carry (or need) any shared FFmpeg library that could be confused
# with the LGPL one Raven loads in-process. Only these packages are built, all static.
GPL_CHILD_PACKAGES = {"x264", "x265"}


def package_wanted(package: Package, community: bool, lgpl: bool, use_gnutls: bool, gpl_child: bool = False) -> bool:
    if package.when == When.never:
        return False
    if gpl_child:
        return package.name in GPL_CHILD_PACKAGES
    if lgpl:
        if package.name in LGPL_EXCLUDED_PACKAGES:
            return False
        if package.name == "gmp" and not use_gnutls:
            return False
        return True
    if package.when == When.community_only and not community:
        return False
    if package.when == When.commercial_only and community:
        return False
    return True


OPENSSL_SEARCH_DIRS = [r"C:\Program Files\OpenSSL\bin", r"C:\Program Files\OpenSSL"]


def copy_openssl_runtime(bin_dir: str) -> None:
    """Ship the OpenSSL DLLs libsrt.dll imports beside it (Windows).

    libsrt is linked against the runner's OpenSSL (its -DOPENSSL_ROOT_DIR); upstream's
    tarball leaves those DLLs behind for delvewheel's --add-path to find at wheel-repair
    time. Raven's drop must load on its own (test_ffmpeg_license.py --dir <drop>/bin), so
    copy exactly what libsrt.dll imports -- read with objdump, falling back to a glob.
    """
    libsrt = os.path.join(bin_dir, "libsrt.dll")
    if not os.path.exists(libsrt):
        return
    wanted = []
    try:
        listing = subprocess.run(
            ["objdump", "-p", libsrt], check=True, stdout=subprocess.PIPE
        ).stdout.decode(errors="replace")
        wanted = [
            m.group(1)
            for m in re.finditer(r"DLL Name:\s*(\S+)", listing)
            if m.group(1).lower().startswith(("libcrypto", "libssl"))
        ]
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"objdump unavailable ({exc}); globbing the OpenSSL runtime instead")
    search_dirs = OPENSSL_SEARCH_DIRS + os.environ.get("PATH", "").split(os.pathsep)
    if not wanted:
        for directory in search_dirs:
            wanted += [
                os.path.basename(p)
                for pattern in ("libcrypto-*.dll", "libssl-*.dll")
                for p in glob.glob(os.path.join(directory, pattern))
            ]
            if wanted:
                break
    for name in dict.fromkeys(wanted):
        for directory in search_dirs:
            candidate = os.path.join(directory, name)
            if os.path.exists(candidate):
                print(f"copying {candidate} -> bin/")
                shutil.copy(candidate, os.path.join(bin_dir, name))
                break
        else:
            raise FileNotFoundError(
                f"libsrt.dll imports {name} but it was not found in {search_dirs[:2]} or PATH"
            )


def gpl_child_configure_arguments() -> list[str]:
    """FFmpeg's configure line for the GPL encoder helper: everything off, then exactly what the
    child's command line uses (Raven's gpl_encoder_child.py): `-f nut -i pipe:0` (the nut
    demuxer, the rawvideo decoder, the pipe protocol), `-c:v libx264` / `libx265`, `-f nut pipe:1`
    (the nut muxer). The ffmpeg program itself auto-selects the filters it inserts (format, null,
    trim...); scale/fps/setpts are enabled for the conversions the CLI may still insert. Static
    link of everything, x265's C++ runtime included; no network, no autodetected system libs."""
    arguments = [
        "--disable-everything",
        "--disable-doc",
        "--disable-network",
        "--disable-autodetect",
        "--disable-ffprobe",
        "--disable-ffplay",
        "--disable-avdevice",
        "--disable-postproc",
        "--enable-gpl",
        "--enable-libx264",
        "--enable-libx265",
        "--enable-encoder=libx264,libx265",
        "--enable-decoder=rawvideo",
        "--enable-demuxer=nut,rawvideo",
        "--enable-muxer=nut",
        "--enable-protocol=pipe,file",
        "--enable-filter=null,format,scale,fps,setpts,trim",
        "--pkg-config-flags=--static",
    ]
    if plat == "Windows":
        # A fully static mingw executable: libgcc, libstdc++ (x265) and winpthread linked in.
        arguments += ["--extra-ldflags=-static", "--extra-libs=-lstdc++ -lpthread"]
    elif plat == "Darwin":
        arguments += ["--extra-libs=-lc++"]
    return arguments


def package_gpl_child(dest_dir: str, output_dir: str) -> str:
    """The helper's tarball: bin/ffmpeg(.exe), src/ (the corresponding source: ffmpeg, x264,
    x265 -- GPLv3 section 6, shipped beside the binary by Raven's installer), CONFIGURE.txt.
    Refuses a binary that still imports a shared FFmpeg / x264 / x265 library."""
    exe_name = "ffmpeg.exe" if plat == "Windows" else "ffmpeg"
    exe = os.path.join(dest_dir, "bin", exe_name)
    if not os.path.exists(exe):
        raise FileNotFoundError(f"{exe} was not built")
    run(["strip", "-S" if plat == "Darwin" else "-s", exe])
    if plat == "Windows":
        listing = subprocess.run(["objdump", "-p", exe], check=True, stdout=subprocess.PIPE).stdout.decode(errors="replace")
        imports = [m.group(1) for m in re.finditer(r"DLL Name:\s*(\S+)", listing)]
        print("ffmpeg.exe imports:", imports)
        bad = [d for d in imports if re.search(r"avcodec|avformat|avutil|swscale|swresample|avfilter|x264|x265|libstdc|libgcc|winpthread", d, re.I)]
        if bad:
            raise RuntimeError(f"the GPL child is not self-contained: it imports {bad}")
    else:
        listing = subprocess.run(["otool", "-L", exe], check=True, stdout=subprocess.PIPE).stdout.decode(errors="replace")
        print("ffmpeg links:", listing)
        bad = [line.strip() for line in listing.splitlines()[1:] if "/usr/lib/" not in line and "/System/" not in line]
        if bad:
            raise RuntimeError(f"the GPL child is not self-contained: it links {bad}")
    version = subprocess.run([exe, "-hide_banner", "-version"], check=True, stdout=subprocess.PIPE).stdout.decode(errors="replace")
    print(version)
    for switch in ("--enable-gpl", "--enable-libx264", "--enable-libx265", "--enable-static", "--disable-shared"):
        if switch not in version:
            raise RuntimeError(f"the GPL child's configure line lacks {switch}")
    encoders = subprocess.run([exe, "-hide_banner", "-encoders"], check=True, stdout=subprocess.PIPE).stdout.decode(errors="replace")
    for name in ("libx264", "libx265"):
        if f" {name} " not in encoders:
            raise RuntimeError(f"the GPL child has no {name} encoder")

    staging = os.path.join(dest_dir, "gpl-child")
    if os.path.exists(staging):
        shutil.rmtree(staging)
    os.makedirs(os.path.join(staging, "bin"))
    os.makedirs(os.path.join(staging, "src"))
    shutil.copy(exe, os.path.join(staging, "bin", exe_name))
    source_dir = os.path.abspath("source")
    for package in [ffmpeg_package] + [p for p in codec_group if p.name in GPL_CHILD_PACKAGES]:
        tarball = os.path.join(source_dir, package.source_filename or package.source_url.split("/")[-1])
        shutil.copy(tarball, os.path.join(staging, "src", os.path.basename(tarball)))
    with open(os.path.join(staging, "CONFIGURE.txt"), "w") as fp:
        fp.write(" ".join(ffmpeg_package.build_arguments) + "\n")
    os.makedirs(output_dir, exist_ok=True)
    output_tarball = os.path.join(output_dir, f"ffmpeg-gpl-child-{get_platform()}.tar.gz")
    run(["tar", "czvf", output_tarball, "-C", staging, "bin", "src", "CONFIGURE.txt"])
    return output_tarball


def download_tars(use_gnutls: bool, community: bool, lgpl: bool = False, gpl_child: bool = False) -> None:
    # Try to download all tars at the start.
    # If there is an curl error, do nothing, then try again in `main()`

    local_libs = library_group
    if use_gnutls:
        local_libs += gnutls_group

    for package in local_libs + codec_group:
        if not package_wanted(package, community, lgpl, use_gnutls, gpl_child):
            continue

        tarball = os.path.join(
            os.path.abspath("source"),
            package.source_filename or package.source_url.split("/")[-1],
        )
        if not os.path.exists(tarball):
            try:
                fetch(package.source_url, tarball)
            except subprocess.CalledProcessError:
                pass


def main():
    global library_group

    parser = argparse.ArgumentParser("build-ffmpeg")
    parser.add_argument("destination")
    parser.add_argument("--community", action="store_true")
    parser.add_argument("--commercial", action="store_true")
    parser.add_argument(
        "--lgpl",
        action="store_true",
        help="Raven's LGPL-2.1 build: community minus x264/x265/gmp/opencore-amr/version3",
    )
    parser.add_argument(
        "--gpl-child",
        action="store_true",
        help="Raven's GPL encoder helper: a static ffmpeg with x264/x265 only (no libraries, no wheel)",
    )
    parser.add_argument(
        "--enable-cuda", action="store_true", help="Enable NVIDIA CUDA support"
    )

    args = parser.parse_args()

    if sum([args.community, args.commercial, args.lgpl, args.gpl_child]) > 1:
        raise ValueError("mutually exclusive")

    dest_dir = args.destination
    community = args.community
    lgpl = args.lgpl
    gpl_child = args.gpl_child
    enable_cuda = args.enable_cuda and plat in {"Linux", "Windows"} and not gpl_child
    del args

    output_dir = os.path.abspath("output")

    # FFmpeg has native TLS backends for macOS and Windows
    use_gnutls = plat == "Linux"

    if plat == "Linux" and os.environ.get("CIBUILDWHEEL") == "1":
        output_dir = "/output"
    output_tarball = os.path.join(
        output_dir, f"ffmpeg-gpl-child-{get_platform()}.tar.gz" if gpl_child else f"ffmpeg-{get_platform()}.tar.gz"
    )

    if os.path.exists(output_tarball):
        return

    builder = Builder(dest_dir=dest_dir)
    builder.create_directories()

    if gpl_child:
        for package in codec_group:
            if package.name in GPL_CHILD_PACKAGES:
                package.static = True
        ffmpeg_package.static = True

    download_tars(use_gnutls, community, lgpl, gpl_child)

    # install packages
    available_tools = set()
    if plat == "Windows":
        available_tools.update(["gperf", "nasm"])

        # print tool locations
        print("PATH", os.environ["PATH"])
        for tool in ["gcc", "g++", "curl", "gperf", "ld", "nasm", "pkg-config"]:
            run(["where", tool])

    with log_group("install python packages"):
        # Raven: pinned -- CMake 4 refuses libsrt 1.5.4's cmake_minimum_required (< 3.5);
        # upstream pinned the same at 7.1.1-5.
        run(["pip", "install", "cmake==3.31.6", "meson", "ninja"])

    # build tools
    if "gperf" not in available_tools:
        builder.build(
            Package(
                name="gperf",
                source_url="http://ftp.gnu.org/pub/gnu/gperf/gperf-3.1.tar.gz",
            ),
            for_builder=True,
        )

    if "nasm" not in available_tools:
        builder.build(
            Package(
                name="nasm",
                source_url="https://www.nasm.us/pub/nasm/releasebuilds/2.14.02/nasm-2.14.02.tar.bz2",
            ),
            for_builder=True,
        )

    ffmpeg_package.build_arguments = [
        "--disable-alsa",
        "--disable-doc",
        # Disable experimental codecs
        "--disable-encoder=avui,dca,mlp,opus,s302m,sonic,sonic_ls,truehd,vorbis",
        "--disable-decoder=sonic",
        "--disable-libtheora",
        "--disable-libfreetype",
        "--disable-libfontconfig",
        "--disable-libbluray",
        "--disable-libopenjpeg",
        (
            "--enable-mediafoundation"
            if plat == "Windows"
            else "--disable-mediafoundation"
        ),
        "--enable-gmp" if (use_gnutls or not lgpl) else "--disable-gmp",
        "--enable-gnutls" if use_gnutls else "--disable-gnutls",
        "--enable-libaom",
        "--enable-libdav1d",
        "--enable-libmp3lame",
        "--enable-libopencore-amrnb" if community else "--disable-libopencore-amrnb",
        "--enable-libopencore-amrwb" if community else "--disable-libopencore-amrwb",
        # (lgpl: the AMR codecs stay off -- they are the other --enable-version3 trigger)
        "--enable-libopus",
        "--enable-libspeex",
        "--enable-libsvtav1",
        "--enable-libsrt" if (community or lgpl) else "--disable-libsrt",
        "--enable-libtwolame",
        "--enable-libvorbis",
        "--enable-libvpx",
        "--enable-libwebp",
        "--enable-libxcb" if plat == "Linux" else "--disable-libxcb",
        "--enable-libxml2",
        "--enable-lzma",
        "--enable-zlib",
    ]

    if gpl_child:
        ffmpeg_package.build_arguments = gpl_child_configure_arguments()
    elif lgpl:
        # LGPL-2.1-or-later: no --enable-version3 (gmp and opencore-amr are the only
        # consumers of it in this recipe and both are off), no GPL and no commercial codecs.
        ffmpeg_package.build_arguments.extend(
            [
                "--disable-libopenh264",
                "--disable-libx264",
                "--disable-libx265",
                "--disable-gpl",
                "--disable-nonfree",
            ]
        )
    else:
        ffmpeg_package.build_arguments.append("--enable-version3")

    if enable_cuda:
        ffmpeg_package.build_arguments.extend(["--enable-nvenc", "--enable-nvdec"])

    if community:
        ffmpeg_package.build_arguments.extend(
            [
                "--enable-libx264",
                "--disable-libopenh264",
                "--enable-libx265",
                "--enable-gpl",
            ]
        )
    elif not lgpl and not gpl_child:
        ffmpeg_package.build_arguments.extend(
            ["--enable-libopenh264", "--disable-libx264", "--enable-libfdk_aac"]
        )

    if plat == "Darwin":
        ffmpeg_package.build_arguments.extend(
            ["--extra-ldflags=-Wl,-ld_classic"] if gpl_child
            else ["--enable-videotoolbox", "--extra-ldflags=-Wl,-ld_classic"]
        )

    if use_gnutls:
        library_group += gnutls_group
    if enable_cuda:
        library_group += [nvheaders]

    package_groups = [library_group + codec_group, [ffmpeg_package]]
    packages = [p for p_list in package_groups for p in p_list]

    for package in packages:
        if not package_wanted(package, community, lgpl, use_gnutls, gpl_child):
            continue

        builder.build(package)

    if gpl_child:
        # Raven --gpl-child: the executable and its corresponding source are the product; the
        # library steps below (mingw runtime DLLs, import libraries, stripping the DLLs) do not
        # apply to a static binary.
        package_gpl_child(dest_dir, output_dir)
        return

    if plat == "Windows":
        # fix .lib files being installed in the wrong directory
        for name in (
            "avcodec",
            "avdevice",
            "avfilter",
            "avformat",
            "avutil",
            "postproc",
            "swresample",
            "swscale",
        ):
            if os.path.exists(os.path.join(dest_dir, "bin", name + ".lib")):
                shutil.move(
                    os.path.join(dest_dir, "bin", name + ".lib"),
                    os.path.join(dest_dir, "lib"),
                )

        # copy some libraries provided by mingw
        mingw_bindir = os.path.dirname(
            subprocess.run(["where", "gcc"], check=True, stdout=subprocess.PIPE)
            .stdout.decode()
            .splitlines()[0]
            .strip()
        )
        for name in (
            "libgcc_s_seh-1.dll",
            "libiconv-2.dll",
            "libstdc++-6.dll",
            "libwinpthread-1.dll",
            "zlib1.dll",
        ):
            shutil.copy(os.path.join(mingw_bindir, name), os.path.join(dest_dir, "bin"))

        # Raven --lgpl: make the drop self-contained (libsrt's OpenSSL runtime).
        if lgpl:
            copy_openssl_runtime(os.path.join(dest_dir, "bin"))

    # find libraries
    if plat == "Darwin":
        libraries = glob.glob(os.path.join(dest_dir, "lib", "*.dylib"))
    elif plat == "Linux":
        libraries = glob.glob(os.path.join(dest_dir, "lib", "*.so"))
    elif plat == "Windows":
        libraries = glob.glob(os.path.join(dest_dir, "bin", "*.dll"))

    # strip libraries
    if plat == "Darwin":
        run(["strip", "-S"] + libraries)
        run(["otool", "-L"] + libraries)
    else:
        run(["strip", "-s"] + libraries)

    # build output tarball
    os.makedirs(output_dir, exist_ok=True)
    run(["tar", "czvf", output_tarball, "-C", dest_dir, "bin", "include", "lib"])


if __name__ == "__main__":
    main()
