import os

# =============================
# Camera
# =============================

CAMERA_ID = 1

CAMERA_INDEX = os.environ.get(
    "CAMERA_RTSP_URL",
    "rtsp://admin:seniorproject2!@192.168.1.209:554/Streaming/Channels/101"
)

CAMERA_RECONNECT_DELAY_SEC = 3.0

FILE_EOF_DRAIN_TIMEOUT_SEC = 10.0

FRAME_W = 1500
FRAME_H = 890
DISPLAY_SCALE = 1.6
MIN_PLATE_BOX_W = 28
MIN_PLATE_BOX_H = 14
MIN_PLATE_AREA_RATIO = 0.001
MIN_PLATE_AREA_PIXELS = 350

PLATE_TRACKER_CANDIDATES = 2

DETECTION_ROI = (50, 300, 1350, 810)

VEHICLE_ENTRY_ROI = (50, 400, 1300, 800)

ENTRY_DIRECTION_SPLIT_Y = (VEHICLE_ENTRY_ROI[1] + VEHICLE_ENTRY_ROI[3]) // 2
DRAW_DETECTION_ROIS = True

# =============================
# Model
# =============================

MODEL_PATH = "best.pt"

CHARACTER_MODEL_PATH = "character.pt"
CHARACTER_MODEL_MIN_CONF = 0.25

PLATE_LINE_SPLIT_RATIO = 0.62

CHARACTER_OVERLAP_RATIO = 0.4

CHARACTER_AMBIGUOUS_MARGIN = 0.20

CHARACTER_GAP_MIN_CONF = 0.10

# =============================
# Backend
# =============================

API_BASE = "https://proactive-gas-station-service-kohl.vercel.app/"

# =============================
# Detection
# =============================


CONF_THRESHOLD = 0.60

PLATE_MODEL_IMGSZ = 960

ENABLE_PLATE_FALLBACK = False
YOLO_VEHICLE_MIN_CONF = 0.18
COLOR_MIN_CONF = 0.40

COLOR_MODEL_PATH = "color.pt"

COLOR_MODEL_MIN_CONF = 0.65

COLOR_MODEL_MIN_INTERVAL_SEC = 0.75

COLOR_REQUIRED_HITS = 2

COLOR_SINGLE_HIT_PROMOTION_MIN_CONF = 0.70
VEHICLE_TRACK_GAP_SEC = 1.5

TRACK_REASSOCIATE_IOU = 0.55
TRACK_DISPLAY_MAX_AGE_SEC = 0.25

EXIT_TRACK_ROI = (400, 240, 1050, 500)
EXIT_ARM_Y = 330
EXIT_CROSS_Y = 280
EXIT_MIN_TRACK_FRAMES = 5
YOLO_PLATE_MIN_CONF = 0.18

YOLO_EVERY_N = 1

OCR_EVERY_N = 15

OCR_MAX_JOBS_PER_TRACK = 3

ENABLE_PROVINCE_OCR = False

OCR_DRAIN_GRACE_SEC = 8


OCR_MIN_CONF = 0.25

PLATE_CHANGE_MIN_CONF_GAIN = 0.15

SINGLE_READ_PROMOTION_MIN_CONF = 0.55

COOLDOWN_SEC = 5

EXIT_AFTER_SEC = 3

UPSCALE_TARGET_W = 1000


DETECTED_GRACE_SEC = 2.0

DEBUG_OCR = bool(os.environ.get("DEBUG_OCR"))

DEBUG_OCR_SAVE_INPUTS = bool(os.environ.get("DEBUG_OCR_SAVE_INPUTS")) or DEBUG_OCR

DEBUG_OCR_SAVE_VARIANTS = bool(os.environ.get("DEBUG_OCR_SAVE_VARIANTS"))
DEBUG_OCR_VERBOSE = bool(os.environ.get("DEBUG_OCR_VERBOSE"))
DEBUG_COLOR = bool(os.environ.get("DEBUG_COLOR"))
DEBUG_THAI_PLATE = bool(os.environ.get("DEBUG_THAI_PLATE"))
DEBUG_PIPELINE = bool(os.environ.get("DEBUG_PIPELINE"))
DEBUG_MAKE_MODEL = bool(os.environ.get("DEBUG_MAKE_MODEL"))

DEBUG_MAKE_MODEL_SAVE_INPUTS = bool(os.environ.get("DEBUG_MAKE_MODEL_SAVE_INPUTS")) or DEBUG_MAKE_MODEL

ENABLE_MAKE_MODEL = bool(os.environ.get("ENABLE_MAKE_MODEL"))
MAKE_MODEL_MIN_CONF = float(os.environ.get("MAKE_MODEL_MIN_CONF", "0.55"))

BRAND_MODEL_PATH = "brand.pt"

MAKE_MODEL_MIN_INTERVAL_SEC = 0.75


ATTRIBUTE_FALLBACK_SEC = 3.0

VEHICLE_FRAME_EDGE_MARGIN = 15

BRAND_ALLOWLIST = {
    "BYD": "byd",
    "Chevrolet": "chevrolet",
    "Honda": "honda",
    "Isuzu": "isuzu",
    "MG": "mg",
    "Mazda": "mazda",
    "MercedesBenz": "mercedesbenz",
    "Mitsubishi": "mitsubishi",
    "Nissan": "nissan",
    "Suzuki": "suzuki",
    "Toyota": "toyota",
}

BRAND_ALLOWLIST_MIN_RAW_CONF = 0.08

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
