/*
  FAT log storage for ESP32-S3 N16R8 builds
 */
#include "options.h"
#include <Arduino.h>
#include "log_storage.h"

#if defined(BOARD_ESP32S3_N16R8)
#include "FFat.h"

static constexpr const char *LOG_PARTITION_LABEL = "logs";
static constexpr const char *LOG_MOUNT_POINT = "/logs";
static constexpr const char *LOG_FILE_PATH = "/remoteid.log";
static bool logs_ready;

bool logs_append_line(const char *line)
{
    if (!logs_ready || line == nullptr) {
        return false;
    }

    File f = FFat.open(LOG_FILE_PATH, FILE_APPEND);
    if (!f) {
        Serial.printf("failed to open %s for append\n", LOG_FILE_PATH);
        return false;
    }

    size_t written = f.println(line);
    f.close();
    return written > 0;
}

bool logs_init(void)
{
    if (logs_ready) {
        return true;
    }

    logs_ready = FFat.begin(true, LOG_MOUNT_POINT, 10, LOG_PARTITION_LABEL);
    if (!logs_ready) {
        Serial.println("logs FAT mount failed");
        return false;
    }

    const uint32_t total = FFat.totalBytes();
    const uint32_t free = FFat.freeBytes();
    Serial.printf("logs total=%u free=%u\n", (unsigned)total, (unsigned)free);

    char line[96];
    snprintf(line, sizeof(line), "%lu boot, total=%u free=%u",
             (unsigned long)millis(),
             (unsigned)total,
             (unsigned)free);
    return logs_append_line(line);
}

#else

bool logs_init(void)
{
    return false;
}

bool logs_append_line(const char *line)
{
    (void)line;
    return false;
}

#endif
