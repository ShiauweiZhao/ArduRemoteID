#!/usr/bin/env python3
"""
Validate the ESP32-S3-WROOM-1U-N16R8 flash layout used by RemoteIDModule.
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_DIR = ROOT / "RemoteIDModule"
PARTITIONS = MODULE_DIR / "partitions-n16r8-logs.csv"
MAKEFILE = MODULE_DIR / "Makefile"
REMOTEID_INO = MODULE_DIR / "RemoteIDModule.ino"
LOG_STORAGE_H = MODULE_DIR / "log_storage.h"
LOG_STORAGE_CPP = MODULE_DIR / "log_storage.cpp"

FLASH_SIZE = 16 * 1024 * 1024
LOG_SIZE = 10 * 1024 * 1024
LOG_OFFSET = 0x600000
APP_SIZE = 0x2F0000


def parse_int(value: str) -> int:
    value = value.strip()
    return int(value, 16 if value.lower().startswith("0x") else 10)


def load_partitions(path: Path) -> dict[str, dict[str, str]]:
    partitions: dict[str, dict[str, str]] = {}
    with path.open(newline="") as f:
        rows = csv.reader(line for line in f if line.strip() and not line.lstrip().startswith("#"))
        for row in rows:
            if len(row) < 5:
                continue
            name, part_type, subtype, offset, size = [field.strip() for field in row[:5]]
            partitions[name] = {
                "type": part_type,
                "subtype": subtype,
                "offset": offset,
                "size": size,
            }
    return partitions


def make_target_body(makefile: str, target: str) -> str:
    match = re.search(rf"^{re.escape(target)}:(?:.*\n)(?P<body>(?:{re.escape(target)}:.*\n)*)", makefile, re.M)
    if not match:
        raise AssertionError(f"missing {target} target")
    return match.group(0)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def check_partition_table() -> None:
    partitions = load_partitions(PARTITIONS)

    require("logs" in partitions, "missing logs partition")
    logs = partitions["logs"]
    require(logs["type"] == "data", "logs partition must use data type")
    require(logs["subtype"] == "fat", "logs partition must use FAT subtype")
    require(parse_int(logs["offset"]) == LOG_OFFSET, "logs partition must start at 0x600000")
    require(parse_int(logs["size"]) == LOG_SIZE, "logs partition must be exactly 10 MiB")
    require(parse_int(logs["offset"]) + parse_int(logs["size"]) == FLASH_SIZE, "logs partition must end at 16 MiB")

    for app in ("app0", "app1"):
        require(app in partitions, f"missing {app} partition")
        require(parse_int(partitions[app]["size"]) == APP_SIZE, f"{app} must be 0x2f0000 bytes")

    require(parse_int(partitions["app0"]["offset"]) == 0x10000, "app0 offset changed unexpectedly")
    require(parse_int(partitions["app1"]["offset"]) == 0x300000, "app1 offset changed unexpectedly")
    require(parse_int(partitions["param"]["offset"]) == 0x5F0000, "param partition must sit before logs")


def check_makefile() -> None:
    makefile = MAKEFILE.read_text()
    all_target = re.search(r"^all:\s*(?P<deps>.+)$", makefile, re.M)
    require(all_target is not None, "missing all target")
    require("esp32s3-n16r8" in all_target.group("deps").split(), "all target must build esp32s3-n16r8")

    target = make_target_body(makefile, "esp32s3-n16r8")
    require("CHIP=esp32s3" in target, "esp32s3-n16r8 must compile for esp32s3")
    require(f"APP_PARTITION_SIZE={APP_SIZE}" in target, "esp32s3-n16r8 must set the OTA app size")
    require("FLASH_SIZE=16MB" in target, "esp32s3-n16r8 must merge as 16MB flash")
    require("PARTITIONS_CSV=partitions-n16r8-logs.csv" in target, "esp32s3-n16r8 must use the N16R8 partition table")
    require("ArduRemoteID-ESP32S3_N16R8.bin" in target, "esp32s3-n16r8 must produce the N16R8 image")
    require("Using $(PARTITIONS_CSV), flash size $(FLASH_SIZE)" in makefile, "build output must print partition and flash size")


def check_log_storage_code() -> None:
    require(LOG_STORAGE_H.exists(), "missing log_storage.h")
    require(LOG_STORAGE_CPP.exists(), "missing log_storage.cpp")

    header = LOG_STORAGE_H.read_text()
    require("bool logs_init(void);" in header, "log_storage.h must declare logs_init")
    require("bool logs_append_line(const char *line);" in header, "log_storage.h must declare logs_append_line")

    code = LOG_STORAGE_CPP.read_text()
    require("#include \"FFat.h\"" in code, "log_storage.cpp must use FFat")
    require("BOARD_ESP32S3_N16R8" in code, "log storage must be limited to the N16R8 build")
    require("FFat.begin(true, LOG_MOUNT_POINT, 10, LOG_PARTITION_LABEL)" in code, "log storage must mount the logs FAT partition")
    require("FFat.open(LOG_FILE_PATH, FILE_APPEND)" in code, "log storage must append to /remoteid.log")
    require("LOG_PARTITION_LABEL = \"logs\"" in code, "log storage must use the logs partition label")
    require("LOG_MOUNT_POINT = \"/logs\"" in code, "log storage must mount at /logs")
    require("LOG_FILE_PATH = \"/remoteid.log\"" in code, "log storage must write /remoteid.log")
    require("FFat.totalBytes()" in code and "FFat.freeBytes()" in code, "log storage must report FAT capacity")

    ino = REMOTEID_INO.read_text()
    require("#include \"log_storage.h\"" in ino, "RemoteIDModule.ino must include log_storage.h")
    require("logs_init();" in ino, "setup() must initialize log storage")


def main() -> int:
    try:
        check_partition_table()
        check_makefile()
        check_log_storage_code()
    except AssertionError as error:
        print(f"check_n16r8_partition.py: {error}", file=sys.stderr)
        return 1

    print("N16R8 partition layout is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
