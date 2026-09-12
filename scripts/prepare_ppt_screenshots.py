#!/usr/bin/env python3
"""
IBVAP — Demo-Day Presentation Screenshots Organizer
Copies and renames key evidence screenshots from e2e/evidence and data/evidence
into demo/screenshots_for_ppt with presentation-friendly slide filenames.
"""

import os
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
EVIDENCE_DIR = BASE_DIR / "e2e" / "evidence"
DATA_EVIDENCE_DIR = BASE_DIR / "data" / "evidence"
PPT_DIR = BASE_DIR / "demo" / "screenshots_for_ppt"

SCREENSHOT_MAP = [
    ("01_login_page.png", "01_operator_clearance_login.png", EVIDENCE_DIR),
    ("02_login_invalid.png", "02_failed_authentication_guard.png", EVIDENCE_DIR),
    ("03_login_success.png", "03_c4isr_tactical_command_console.png", EVIDENCE_DIR),
    ("04_nav_cameras.png", "04_tactical_matrix_grid.png", EVIDENCE_DIR),
    ("05_nav_media.png", "05_tactical_video_studio.png", EVIDENCE_DIR),
    ("06_nav_incidents.png", "06_threat_queue_incident_triage.png", EVIDENCE_DIR),
    ("07_nav_evidence.png", "07_evidence_locker_vault.png", EVIDENCE_DIR),
    ("08_nav_frs.png", "08_frs_biometric_intelligence.png", EVIDENCE_DIR),
    ("09_nav_map.png", "09_situational_geospatial_map.png", EVIDENCE_DIR),
    ("10_nav_settings.png", "10_system_configuration_matrix.png", EVIDENCE_DIR),
    ("11_nav_reports.png", "11_audit_reports_compliance.png", EVIDENCE_DIR),
    ("12_video_studio_upload_btn.png", "12_video_studio_upload_control.png", EVIDENCE_DIR),
    ("13_upload_vehicle_plate.png", "13_surveillance_media_ingestion.png", EVIDENCE_DIR),
    ("14_upload_rejected_txt.png", "14_unsupported_file_rejection.png", EVIDENCE_DIR),
    ("16_video_preview_playback.png", "15_airgap_video_player_playback.png", EVIDENCE_DIR),
    ("17_analysis_modal_open.png", "16_edge_cv_pipeline_launch.png", EVIDENCE_DIR),
    ("18_analysis_progress_t1.png", "17_analysis_progress_timestamp1.png", EVIDENCE_DIR),
    ("19_analysis_progress_t2.png", "18_analysis_progress_timestamp2.png", EVIDENCE_DIR),
    ("20_analysis_progress_t3.png", "19_analysis_progress_timestamp3.png", EVIDENCE_DIR),
    ("21_realtime_detections.png", "20_realtime_detections_feed.png", EVIDENCE_DIR),
    ("22_job_completion_summary.png", "21_job_completion_telemetry.png", EVIDENCE_DIR),
    ("23_zone_line_saved.png", "22_virtual_fence_tripwire_line.png", EVIDENCE_DIR),
    ("24_zone_polygon_saved.png", "23_virtual_fence_exclusion_polygon.png", EVIDENCE_DIR),
    ("25_zone_polygon_deleted.png", "24_virtual_fence_zone_lifecycle.png", EVIDENCE_DIR),
    ("26_zone_intrusion_incident.png", "25_perimeter_breach_escalation.png", EVIDENCE_DIR),
    ("27_track_trail_rendered.png", "26_centroid_tracker_path_trail.png", EVIDENCE_DIR),
    ("28_active_tracks_filtered.png", "27_active_tracks_dwell_speed.png", EVIDENCE_DIR),
    ("29_cooldown_stable.png", "28_cooldown_suppression_integrity.png", EVIDENCE_DIR),
    ("31_anpr_search_result.png", "29_anpr_license_plate_extraction.png", EVIDENCE_DIR),
    ("32_frs_suspect_enrolled.png", "30_frs_suspect_gallery_enrollment.png", EVIDENCE_DIR),
    ("33_frs_watchlist_match_incident.png", "31_sface_biometric_face_match.png", EVIDENCE_DIR),
    ("34_night_crossing_incident.png", "32_night_clahe_low_luma_detection.png", EVIDENCE_DIR),
    ("35_evidence_vault_playback.png", "33_bsa63_evidence_vault_playback.png", EVIDENCE_DIR),
    ("36_evidence_hash_verified.png", "34_sha256_cryptographic_verification.png", EVIDENCE_DIR),
    ("37_pdf_report_downloaded.png", "35_bsa63_court_admissible_pdf_report.png", EVIDENCE_DIR),
    ("38_json_report_downloaded.png", "36_structured_json_evidence_manifest.png", EVIDENCE_DIR),
    ("39_map_camera_pin.png", "37_situational_map_bop_tactical_layer.png", EVIDENCE_DIR),
    ("40_map_incident_drawer.png", "38_incident_marker_detail_drawer.png", EVIDENCE_DIR),
    ("41_tactical_hud_clock.png", "39_hud_dual_clock_military_telemetry.png", EVIDENCE_DIR),
    ("42_share_link_restored.png", "40_restored_session_share_links.png", EVIDENCE_DIR),
    ("43_patrol_st1.png", "41_patrol_tour_station1.png", EVIDENCE_DIR),
    ("43_patrol_st2.png", "42_patrol_tour_station2.png", EVIDENCE_DIR),
    ("43_patrol_st3.png", "43_patrol_tour_station3.png", EVIDENCE_DIR),
    ("43_patrol_st4.png", "44_patrol_tour_station4.png", EVIDENCE_DIR),
    ("43_patrol_st5.png", "45_patrol_tour_station5.png", EVIDENCE_DIR),
    ("43_patrol_st6.png", "46_patrol_tour_station6.png", EVIDENCE_DIR),
    ("49_camera_add_invalid.png", "47_invalid_rtsp_optical_link_fail.png", EVIDENCE_DIR),
    ("50_network_resilience_offline.png", "48_network_resilience_airgap_banner.png", EVIDENCE_DIR),
    ("52_airgap_map_local_tiles.png", "49_airgap_isolated_tile_cache.png", EVIDENCE_DIR),
    ("53_rtsp_camera_online.png", "50_live_rtsp_network_camera_provisioned.png", DATA_EVIDENCE_DIR),
    ("54_rtsp_live_detections.png", "51_live_rtsp_realtime_cv_detections.png", DATA_EVIDENCE_DIR),
]

def main():
    PPT_DIR.mkdir(parents=True, exist_ok=True)
    copied = 0
    missing = 0

    print("=== IBVAP Presentation Screenshots Builder ===")
    print(f"Target: {PPT_DIR}\n")

    for src_name, dst_name, src_dir in SCREENSHOT_MAP:
        src_path = src_dir / src_name
        dst_path = PPT_DIR / dst_name

        if src_path.exists():
            shutil.copy2(src_path, dst_path)
            size_kb = dst_path.stat().st_size / 1024.0
            print(f"  ✓ {dst_name:<46} ({size_kb:.1f} KB) <- {src_name}")
            copied += 1
        else:
            print(f"  ⚠ MISSING: {src_path}")
            missing += 1

    print(f"\nCompleted: {copied} copied, {missing} missing out of {len(SCREENSHOT_MAP)} items.")
    return 0 if missing == 0 else 1

if __name__ == "__main__":
    exit(main())
