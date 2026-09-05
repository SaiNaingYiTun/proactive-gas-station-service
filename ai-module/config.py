import os

# =============================
# Camera
# =============================

CAMERA_ID = 1

CAMERA_INDEX = os.environ.get(
    "CAMERA_RTSP_URL",
    "rtsp://admin:seniorproject2!@192.168.1.209:554/Streaming/Channels/101"
)

FRAME_W = 1500
FRAME_H = 890
DISPLAY_SCALE = 1.6
# Plates are small while a car is still approaching this camera.  These values
# reject detector noise, but still allow a 60-70px wide plate to be collected
# over several frames and enlarged before OCR.
MIN_PLATE_BOX_W = 28
MIN_PLATE_BOX_H = 14
MIN_PLATE_AREA_RATIO = 0.001
MIN_PLATE_AREA_PIXELS = 350
# OCR used to wait for four plate detections before it queued its first crop.
# That is too long for vehicles that move through the driveway at a normal
# brisk speed: the vehicle is tracked, but it may leave before OCR ever runs.
# Two consecutive valid boxes still let BurstTracker select the sharper crop;
# PlateStabilizer below in main.py still requires two OCR reads before a plate
# is accepted, so this does not turn a single OCR hallucination into an event.
PLATE_TRACKER_CANDIDATES = 2

# Keep detection only around the condo gate / driveway area.
# This camera sees the public road too, so ignore everything outside the actual entry zone.
DETECTION_ROI = (
    250,
    350,
    1350,
    810,
)

# A vehicle must have its centre in this rectangle before it is used for colour
# classification.  Keep this separate from the plate ROI: the vehicle model
# runs on the complete image so its bounding box is not cut off at an ROI edge.
# The live window draws this in yellow; tune these four values to the driveway.
# The plate area remains narrow, but a vehicle can enter from the left side of
# the driveway.  Keep the top edge below the public road to avoid classifying
# passing traffic as a station visitor.
# Only create vehicle sessions after a car has entered the station driveway.
# This excludes public-road traffic visible across the upper part of the frame.
VEHICLE_ENTRY_ROI = (200, 350, 1300, 800)
DRAW_DETECTION_ROIS = True

# =============================
# Model
# =============================

MODEL_PATH = "best.pt"
# The trained detector recognizes registration characters, digits, and a
# province-code class.  It is used as the primary exit-plate recognizer.
CHARACTER_MODEL_PATH = "character.pt"
CHARACTER_MODEL_MIN_CONF = 0.25
# A plate crop is split into a registration-number band (top) and a
# province-name band (bottom).  Keep this ratio in sync everywhere the crop
# is divided, so a character model detection cannot be attributed to the
# wrong band just because it shares the same x-position as a real one.
PLATE_LINE_SPLIT_RATIO = 0.62

# =============================
# Backend
# =============================

API_BASE = "http://localhost:8000"

# =============================
# Detection
# =============================

# A plate detector confidence below this value produced repeated detections of
# foliage and the sign frame in this camera.  OCR must never be used to decide
# whether an object is a plate; it is only used after this gate succeeds.
# The running process must be restarted after changing this value.
CONF_THRESHOLD = 0.60
# The colour/contour fallback is intentionally disabled for live OCR.  On this
# camera it mistakes white car bodywork and road markings for plates, which
# then wastes OCR jobs and produces misleading "reading" tracks.
ENABLE_PLATE_FALLBACK = False
YOLO_VEHICLE_MIN_CONF = 0.18
COLOR_MIN_CONF = 0.40
# `color.pt` is a YOLO classification model trained for vehicle colours.
# Keep HSV only as a fallback when this model cannot make a confident choice.
COLOR_MODEL_PATH = "color.pt"
# A 0.58 green prediction on a mostly white truck was caused by foliage in a
# loose vehicle box.  Require a stronger classifier decision; HSV remains the
# fallback for lower-confidence predictions.
COLOR_MODEL_MIN_CONF = 0.65
# Colour is secondary metadata.  It runs only after at least one plate crop
# has completed OCR, then no more often than this interval.  The time-based
# throttle makes the first colour result available promptly for a car that is
# about to leave, while keeping the GPU free during plate/OCR work.
COLOR_MODEL_MIN_INTERVAL_SEC = 0.75
# Do not show or send a colour based on a single frame.  White and silver are
# especially sensitive to glare, so wait for the same class twice.
COLOR_REQUIRED_HITS = 2
VEHICLE_TRACK_GAP_SEC = 1.5
# When ByteTrack briefly loses a close vehicle and assigns a new ID, preserve
# its existing plate/color session if the new box substantially overlaps it.
TRACK_REASSOCIATE_IOU = 0.55
TRACK_DISPLAY_MAX_AGE_SEC = 0.25
# Coordinates refer to the resized 1500x890 processing frame.  A real exit
# starts low in the driveway, then crosses upward through this corridor.
EXIT_TRACK_ROI = (400, 240, 1050, 500)
EXIT_ARM_Y = 330
EXIT_CROSS_Y = 280
EXIT_MIN_TRACK_FRAMES = 5
YOLO_PLATE_MIN_CONF = 0.18

YOLO_EVERY_N = 1

OCR_EVERY_N = 15
# Submit at most two sharp crops per tracked vehicle.  They can be queued
# while the first OCR job is still running, which helps fast vehicles without
# repeatedly OCRing a vehicle that remains stopped for a long time.
OCR_MAX_JOBS_PER_TRACK = 2
# Province is optional for this application.  Skipping it removes three
# EasyOCR passes from every plate job and materially reduces OCR latency.
ENABLE_PROVINCE_OCR = False
# Preserve a disappeared track briefly while its queued OCR crops drain.
OCR_DRAIN_GRACE_SEC = 8

# Never turn a one- or two-character OCR hallucination into an entry event.
# A valid Thai plate is still stabilized across multiple frames, so accept a
# readable low-confidence primary OCR result instead of discarding it for a
# worse preprocessing fallback.
OCR_MIN_CONF = 0.25
# Once a plate is stable for one tracked vehicle, do not replace it with a
# different OCR spelling unless the new reading is meaningfully more certain.
PLATE_CHANGE_MIN_CONF_GAIN = 0.15

COOLDOWN_SEC = 5

EXIT_AFTER_SEC = 3

UPSCALE_TARGET_W = 1000

DEBUG_OCR = bool(os.environ.get("DEBUG_OCR"))
# Normal debug mode stores one original plate crop per OCR attempt.  It does
# not store the internal preprocessing variants unless explicitly requested.
DEBUG_OCR_SAVE_INPUTS = bool(os.environ.get("DEBUG_OCR_SAVE_INPUTS")) or DEBUG_OCR
# Set this only when diagnosing preprocessing; it writes the three internal
# preprocessing variants for every OCR pass.
DEBUG_OCR_SAVE_VARIANTS = bool(os.environ.get("DEBUG_OCR_SAVE_VARIANTS"))
DEBUG_OCR_VERBOSE = bool(os.environ.get("DEBUG_OCR_VERBOSE"))
DEBUG_COLOR = bool(os.environ.get("DEBUG_COLOR"))
DEBUG_THAI_PLATE = bool(os.environ.get("DEBUG_THAI_PLATE"))
DEBUG_PIPELINE = bool(os.environ.get("DEBUG_PIPELINE"))
DEBUG_MAKE_MODEL = bool(os.environ.get("DEBUG_MAKE_MODEL"))

ENABLE_MAKE_MODEL = bool(os.environ.get("ENABLE_MAKE_MODEL"))
MAKE_MODEL_MIN_CONF = float(os.environ.get("MAKE_MODEL_MIN_CONF", "0.55"))

# =============================
# OCR
# =============================



PLATE_NUMBER_ALLOWLIST = (
    "0123456789"
    "กขคงจฉชซญดตถทธนบปผฝพฟภมยรลวศษสหอฮ"
)

PROVINCE_ALLOWLIST = (
    "กขคงจฉชซญดตถทธนบปผฝพฟภมยรลวศษสหอฮ"
    "ะาิีึืุูเแโใไ็่้๊๋์"
)

# =============================
# Province List
# =============================

THAI_PROVINCES = [
    "กรุงเทพมหานคร","กระบี่","กาญจนบุรี","กาฬสินธุ์","กำแพงเพชร",
    "ขอนแก่น","จันทบุรี","ฉะเชิงเทรา","ชลบุรี","ชัยนาท","ชัยภูมิ",
    "ชุมพร","เชียงราย","เชียงใหม่","ตรัง","ตราด","ตาก",
    "นครนายก","นครปฐม","นครพนม","นครราชสีมา",
    "นครศรีธรรมราช","นครสวรรค์","นนทบุรี","นราธิวาส",
    "น่าน","บึงกาฬ","บุรีรัมย์","ปทุมธานี",
    "ประจวบคีรีขันธ์","ปราจีนบุรี","ปัตตานี",
    "พระนครศรีอยุธยา","พะเยา","พังงา","พัทลุง",
    "พิจิตร","พิษณุโลก","เพชรบุรี","เพชรบูรณ์",
    "แพร่","ภูเก็ต","มหาสารคาม","มุกดาหาร",
    "แม่ฮ่องสอน","ยโสธร","ยะลา","ร้อยเอ็ด",
    "ระนอง","ระยอง","ราชบุรี","ลพบุรี",
    "ลำปาง","ลำพูน","เลย","ศรีสะเกษ",
    "สกลนคร","สงขลา","สตูล","สมุทรปราการ",
    "สมุทรสงคราม","สมุทรสาคร","สระแก้ว",
    "สระบุรี","สิงห์บุรี","สุโขทัย",
    "สุพรรณบุรี","สุราษฎร์ธานี","สุรินทร์",
    "หนองคาย","หนองบัวลำภู","อ่างทอง",
    "อำนาจเจริญ","อุดรธานี","อุตรดิตถ์",
    "อุทัยธานี","อุบลราชธานี"
]
