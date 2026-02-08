import os
import csv
import platform
from collections import defaultdict
from datetime import datetime

# ==============================
# OS-SPECIFIC IMPORTS
# ==============================
if platform.system() == "Windows":
    import win32security
else:
    import pwd


# ==============================
# HELPER FUNCTIONS
# ==============================
def get_file_owner(path):
    try:
        if platform.system() == "Windows":
            sd = win32security.GetFileSecurity(
                path, win32security.OWNER_SECURITY_INFORMATION
            )
            owner_sid = sd.GetSecurityDescriptorOwner()
            name, domain, _ = win32security.LookupAccountSid(None, owner_sid)
            return f"{domain}\\{name}"
        else:
            return pwd.getpwuid(os.stat(path).st_uid).pw_name
    except Exception:
        return "Unknown"


def format_time(timestamp):
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


# ==============================
# DUPLICATE DETECTION
# ==============================
def find_duplicate_files(folder_path):
    files_map = defaultdict(list)

    for root, dirs, files in os.walk(folder_path):
        for file in files:
            full_path = os.path.join(root, file)
            try:
                stat = os.stat(full_path)
                key = (file, stat.st_size)
                files_map[key].append(full_path)
            except OSError:
                pass

    return {k: v for k, v in files_map.items() if len(v) > 1}


# ==============================
# CLEANUP + CSV DATA COLLECTION
# ==============================
def choose_file_to_keep(paths, strategy="oldest"):
    if strategy == "newest":
        return max(paths, key=lambda p: os.stat(p).st_ctime)
    return min(paths, key=lambda p: os.stat(p).st_ctime)


def cleanup_and_collect(duplicates, dry_run=True, strategy="oldest"):
    records = []

    for (filename, size), paths in duplicates.items():
        keep = choose_file_to_keep(paths, strategy)

        for path in paths:
            stat = os.stat(path)
            status = "REMAINING"

            if path != keep:
                status = "DELETED"
                if dry_run:
                    print("[DRY-RUN] Would delete:", path)
                else:
                    try:
                        os.remove(path)
                        print("[DELETED]", path)
                    except Exception as e:
                        status = "ERROR"
                        print("[ERROR]", path, "-", e)

            records.append([
                filename,
                path,
                size,
                get_file_owner(path),
                format_time(stat.st_ctime),
                format_time(stat.st_mtime),
                status
            ])

    return records


# ==============================
# CSV EXPORT
# ==============================
def export_final_csv(records, output_csv):
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "filename",
            "path",
            "size_bytes",
            "owner",
            "date_created",
            "date_modified",
            "status"
        ])
        writer.writerows(records)


# ==============================
# MAIN
# ==============================
if __name__ == "__main__":

    # 🔧 CONFIGURATION
    folder_to_scan = r"D:\Programming\Data_clean"
    output_csv = r"D:\Programming\Data_clean\dupclean_files.csv"

    DRY_RUN = True          # 🔴 SET False TO ACTUALLY DELETE
    STRATEGY = "newest"     # "oldest" or "newest"

    print("\nScanning:", folder_to_scan)
    print("=" * 70)

    duplicates = find_duplicate_files(folder_to_scan)

    if not duplicates:
        print("No duplicate files found.")
        exit()

    records = cleanup_and_collect(
        duplicates,
        dry_run=DRY_RUN,
        strategy=STRATEGY
    )

    export_final_csv(records, output_csv)

    # ==============================
    # SUMMARY PRINT
    # ==============================
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)

    kept = [r for r in records if r[-1] == "REMAINING"]
    deleted = [r for r in records if r[-1] == "DELETED"]

    print("\nFILES REMAINING:")
    for r in kept:
        print(" ✔", r[1])

    print("\nFILES DELETED:" if not DRY_RUN else "\nFILES MARKED FOR DELETION:")
    for r in deleted:
        print(" ✖", r[1])

    print(f"\nCSV report generated at:\n{output_csv}")

    if DRY_RUN:
        print("\n⚠ Dry-run mode enabled — no files were deleted.")
    else:
        print("\n✔ Cleanup completed.")
