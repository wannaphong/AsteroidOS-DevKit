"""
AsteroidOS IPK Packager.

Provides pure-Python creation and extraction of .ipk (Debian/OPKG) packages
used by AsteroidOS.
"""

from __future__ import annotations

import hashlib
import io
import os
from pathlib import Path
import stat
import tarfile
import time
from typing import Dict, List, Optional, Tuple, Union


class ArArchive:
    """Pure-Python GNU ar archive reader and writer."""

    MAGIC = b"!<arch>\n"

    @staticmethod
    def create(output_path: Union[str, Path], entries: List[Tuple[str, bytes, Optional[int]]]) -> None:
        """
        Create a GNU ar archive.

        Args:
            output_path: Path to write the archive.
            entries: List of (filename, data_bytes, optional_mode) tuples.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        now = int(time.time())
        with open(output_path, "wb") as f:
            f.write(ArArchive.MAGIC)
            for name, data, file_mode in entries:
                mode = file_mode if file_mode is not None else 0o100644
                size = len(data)
                # GNU ar header is 60 bytes:
                # 0-15:  file name (16 chars, space padded)
                # 16-27: mtime (12 chars, decimal)
                # 28-33: uid (6 chars)
                # 34-39: gid (6 chars)
                # 40-47: mode (8 chars, octal)
                # 48-57: size (10 chars, decimal)
                # 58-59: trailer (`\n)
                # Format name ending with '/' for GNU ar standard compatibility or trailing spaces
                name_field = f"{name:<16}"[:16]
                mtime_field = f"{now:<12}"[:12]
                uid_field = f"{0:<6}"[:6]
                gid_field = f"{0:<6}"[:6]
                mode_field = f"{oct(mode)[2:]:>6}  "[:8]
                size_field = f"{size:<10}"[:10]
                trailer = b"`\n"

                header = (
                    name_field.encode("ascii")
                    + mtime_field.encode("ascii")
                    + uid_field.encode("ascii")
                    + gid_field.encode("ascii")
                    + mode_field.encode("ascii")
                    + size_field.encode("ascii")
                    + trailer
                )
                assert len(header) == 60, f"Ar header must be 60 bytes, got {len(header)}"

                f.write(header)
                f.write(data)
                if size % 2 != 0:
                    f.write(b"\n")

    @staticmethod
    def read(archive_path: Union[str, Path]) -> Dict[str, bytes]:
        """
        Read all members of an ar archive.

        Returns:
            Dict mapping member filename to raw bytes content.
        """
        archive_path = Path(archive_path)
        with open(archive_path, "rb") as f:
            magic = f.read(8)
            if magic != ArArchive.MAGIC:
                raise ValueError(f"Invalid ar archive magic: {magic!r}")

            result: Dict[str, bytes] = {}
            while True:
                header = f.read(60)
                if not header or len(header) < 60:
                    break

                raw_name = header[0:16].decode("ascii", errors="replace").strip()
                # Clean GNU slash suffix if present
                clean_name = raw_name.rstrip("/")
                raw_size = header[48:58].decode("ascii", errors="replace").strip()
                size = int(raw_size)

                data = f.read(size)
                result[clean_name] = data
                # Account for odd-byte alignment padding
                if size % 2 != 0:
                    f.read(1)

            return result


class IpkPackager:
    """Helper for building and inspecting AsteroidOS .ipk packages."""

    @staticmethod
    def build_control_file(fields: Dict[str, str]) -> bytes:
        """Formats an OPKG/Debian control file from a dictionary of fields."""
        lines = []
        # Standard field order
        standard_keys = [
            "Package",
            "Version",
            "Description",
            "Section",
            "Priority",
            "Maintainer",
            "Architecture",
            "Depends",
            "Installed-Size",
        ]
        written = set()

        for key in standard_keys:
            if key in fields and fields[key] is not None:
                lines.append(f"{key}: {fields[key]}")
                written.add(key)

        for key, value in fields.items():
            if key not in written and value is not None:
                lines.append(f"{key}: {value}")

        return "\n".join(lines).encode("utf-8") + b"\n"

    @classmethod
    def create_ipk(
        cls,
        output_file: Union[str, Path],
        control_fields: Dict[str, str],
        data_files: List[Tuple[Union[str, Path], str, Optional[int]]],
        postinst: Optional[str] = None,
        prerm: Optional[str] = None,
    ) -> Path:
        """
        Create a complete .ipk package.

        Args:
            output_file: Destination .ipk file path.
            control_fields: Dictionary containing Package, Version, Architecture, Description, etc.
            data_files: List of (source_path_or_content, dest_rel_path, optional_mode).
                        dest_rel_path should start with leading slash or usr/...
                        If source is str/bytes not existing on disk, it is treated as inline content.
            postinst: Optional bash script content for post-installation.
            prerm: Optional bash script content for pre-removal.

        Returns:
            Path to the created .ipk package.
        """
        output_file = Path(output_file)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        now = int(time.time())

        # 1. Build data.tar.gz
        data_tar_buf = io.BytesIO()
        md5_sums: List[Tuple[str, str]] = []
        installed_size_bytes = 0

        # Sort files by path for deterministic builds
        sorted_files = sorted(data_files, key=lambda x: str(x[1]).lstrip("/"))

        with tarfile.open(fileobj=data_tar_buf, mode="w:gz") as tar:
            # Keep track of created parent directories
            created_dirs = set()

            for src, dest_path, mode in sorted_files:
                clean_dest = str(dest_path).lstrip("/")
                parts = clean_dest.split("/")

                # Ensure parent dirs are created in tar
                current_dir = ""
                for part in parts[:-1]:
                    current_dir = f"{current_dir}/{part}" if current_dir else part
                    tar_dir_name = f"./{current_dir}/"
                    if tar_dir_name not in created_dirs:
                        dinfo = tarfile.TarInfo(name=tar_dir_name)
                        dinfo.type = tarfile.DIRTYPE
                        dinfo.mode = 0o755
                        dinfo.mtime = now
                        tar.addfile(dinfo)
                        created_dirs.add(tar_dir_name)

                # Check if file on disk is a symlink
                if isinstance(src, (str, Path)) and os.path.islink(str(src)):
                    link_target = os.readlink(str(src))
                    tar_path = f"./{clean_dest}"
                    tinfo = tarfile.TarInfo(name=tar_path)
                    tinfo.type = tarfile.SYMTYPE
                    tinfo.linkname = link_target
                    tinfo.mode = 0o777
                    tinfo.mtime = now
                    tar.addfile(tinfo)
                    continue

                # Determine file content
                is_file_on_disk = False
                if isinstance(src, (str, Path)) and os.path.exists(str(src)) and os.path.isfile(str(src)):
                    with open(str(src), "rb") as sf:
                        content_bytes = sf.read()
                    is_file_on_disk = True
                elif isinstance(src, bytes):
                    content_bytes = src
                elif isinstance(src, str):
                    content_bytes = src.encode("utf-8")
                else:
                    raise TypeError(f"Unsupported source data type: {type(src)}")

                # Track size & md5
                installed_size_bytes += len(content_bytes)
                md5_hash = hashlib.md5(content_bytes).hexdigest()
                md5_sums.append((clean_dest, md5_hash))

                # Default file permissions:
                # 0755 if in /usr/bin or starts with shebang, else 0644
                if mode is None:
                    if "bin/" in clean_dest or content_bytes.startswith(b"#!"):
                        mode = 0o755
                    else:
                        mode = 0o644

                tar_path = f"./{clean_dest}"
                tinfo = tarfile.TarInfo(name=tar_path)
                tinfo.size = len(content_bytes)
                tinfo.mode = mode
                tinfo.mtime = now
                tinfo.type = tarfile.REGTYPE
                tar.addfile(tinfo, io.BytesIO(content_bytes))

        data_tar_bytes = data_tar_buf.getvalue()

        # Update Installed-Size (in KB)
        if "Installed-Size" not in control_fields:
            control_fields["Installed-Size"] = str(max(1, (installed_size_bytes + 1023) // 1024))

        # 2. Build control.tar.gz
        control_tar_buf = io.BytesIO()
        with tarfile.open(fileobj=control_tar_buf, mode="w:gz") as tar:
            # Add ./control
            control_content = cls.build_control_file(control_fields)
            cinfo = tarfile.TarInfo(name="./control")
            cinfo.size = len(control_content)
            cinfo.mode = 0o644
            cinfo.mtime = now
            tar.addfile(cinfo, io.BytesIO(control_content))

            # Add ./md5sums
            if md5_sums:
                md5_lines = "".join(f"{h}  {path}\n" for path, h in md5_sums).encode("utf-8")
                minfo = tarfile.TarInfo(name="./md5sums")
                minfo.size = len(md5_lines)
                minfo.mode = 0o644
                minfo.mtime = now
                tar.addfile(minfo, io.BytesIO(md5_lines))

            # Add postinst if provided
            if postinst:
                postinst_bytes = postinst.strip().encode("utf-8") + b"\n"
                pinfo = tarfile.TarInfo(name="./postinst")
                pinfo.size = len(postinst_bytes)
                pinfo.mode = 0o755
                pinfo.mtime = now
                tar.addfile(pinfo, io.BytesIO(postinst_bytes))

            # Add prerm if provided
            if prerm:
                prerm_bytes = prerm.strip().encode("utf-8") + b"\n"
                prinfo = tarfile.TarInfo(name="./prerm")
                prinfo.size = len(prerm_bytes)
                prinfo.mode = 0o755
                prinfo.mtime = now
                tar.addfile(prinfo, io.BytesIO(prerm_bytes))

        control_tar_bytes = control_tar_buf.getvalue()

        # 3. Combine into GNU ar archive
        ar_entries = [
            ("debian-binary", b"2.0\n", 0o100644),
            ("control.tar.gz", control_tar_bytes, 0o100644),
            ("data.tar.gz", data_tar_bytes, 0o100644),
        ]

        ArArchive.create(output_file, ar_entries)
        return output_file

    @classmethod
    def extract_ipk(cls, ipk_path: Union[str, Path], dest_dir: Union[str, Path]) -> Dict[str, bytes]:
        """
        Extract all components of an IPK package into dest_dir.

        Returns:
            Dict containing parsed control fields.
        """
        ipk_path = Path(ipk_path)
        dest_dir = Path(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)

        members = ArArchive.read(ipk_path)
        if "control.tar.gz" not in members or "data.tar.gz" not in members:
            raise ValueError(f"Malformed IPK package: missing control or data archive.")

        # Extract data.tar.gz
        with tarfile.open(fileobj=io.BytesIO(members["data.tar.gz"]), mode="r:gz") as tar:
            if hasattr(tarfile, "data_filter"):
                tar.extractall(path=dest_dir, filter="data")
            else:
                tar.extractall(path=dest_dir)

        # Extract and parse control
        control_fields = {}
        with tarfile.open(fileobj=io.BytesIO(members["control.tar.gz"]), mode="r:gz") as tar:
            try:
                control_member = tar.extractfile("./control")
                if control_member:
                    content = control_member.read().decode("utf-8", errors="replace")
                    for line in content.splitlines():
                        if ":" in line and not line.startswith(" "):
                            key, val = line.split(":", 1)
                            control_fields[key.strip()] = val.strip()
            except KeyError:
                pass

        return control_fields

    @classmethod
    def read_control(cls, ipk_path: Union[str, Path]) -> Dict[str, str]:
        """Reads and parses the control file from an IPK without full extraction."""
        members = ArArchive.read(ipk_path)
        if "control.tar.gz" not in members:
            raise ValueError("No control.tar.gz in IPK package.")

        control_fields = {}
        with tarfile.open(fileobj=io.BytesIO(members["control.tar.gz"]), mode="r:gz") as tar:
            member = tar.extractfile("./control")
            if member:
                content = member.read().decode("utf-8", errors="replace")
                for line in content.splitlines():
                    if ":" in line and not line.startswith(" "):
                        k, v = line.split(":", 1)
                        control_fields[k.strip()] = v.strip()
        return control_fields
