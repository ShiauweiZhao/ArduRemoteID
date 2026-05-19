/*
  FAT log storage for ESP32-S3 N16R8 builds
 */
#pragma once

bool logs_init(void);
bool logs_append_line(const char *line);
