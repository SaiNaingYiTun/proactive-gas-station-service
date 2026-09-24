import os

# =============================
# Camera
# =============================

CAMERA_ID = 1

CAMERA_INDEX = os.environ.get(
    "CAMERA_RTSP_URL",
    "rtsp://admin:seniorproject2!@192.168.1.209:554/Streaming/Channels/101"
)
# A stream drop previously just crashed the whole process (a transient
# network/camera hiccup then required a manual restart).  Keep retrying at
# this interval, indefinitely, rather than giving up -- an unattended
# station may have nobody watching to notice and restart it.
CAMERA_RECONNECT_DELAY_SEC = 3.0
# A recorded video file has no more frames once it reaches its end, but the
# OCR/colour/make/backend pipeline runs on background worker threads and may
# still be mid-job for the last few vehicles seen. Give it this long to
# actually finish and reach the backend before the workers are torn down,
# instead of silently dropping whatever was still in flight. Live streams
# never hit this -- they reconnect instead of ending, so nothing is waiting.
FILE_EOF_DRAIN_TIMEOUT_SEC = 10.0

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
    50,
    300,
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
VEHICLE_ENTRY_ROI = (50, 400, 1300, 800)
# The road this camera watches is toward the TOP of frame and the station is
# toward the BOTTOM, so a vehicle's box position the first time its session
# is created is a real, usable signal for which direction it's moving: one
# arriving from the road crosses into VEHICLE_ENTRY_ROI right at its top
# edge, while one already inside (parked, now leaving) is first (re)tracked
# well below that -- its earlier entry session has almost always already
# been retired (see VEHICLE_TRACK_GAP_SEC) by the time it starts moving
# again minutes later, so this "first box position" is a fresh reading, not
# a stale one left over from when it entered. Direction matters because the
# two kinds of traffic get framed differently over time: entering vehicles
# get WORSE framed the longer they're waited on (they approach the camera
# and eventually get too close/edge-clipped -- see VEHICLE_FRAME_EDGE_MARGIN
# below); exiting vehicles move away from that same close-in zone, so they
# get BETTER framed with time. The ROI's own vertical midpoint is a
# reasonable starting guess for the split, not a measured value -- retune it
# if real traffic splits somewhere else on this camera.
ENTRY_DIRECTION_SPLIT_Y = (VEHICLE_ENTRY_ROI[1] + VEHICLE_ENTRY_ROI[3]) // 2
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
# YOLO's own NMS only suppresses duplicate boxes of the SAME class; two
# different classes (e.g. "9" and "0") proposed for the same physical glyph
# both survive independently and can push a plate over the max digit count.
# Two detected characters overlapping by at least this fraction of the
# smaller box's area are treated as the same physical position.
CHARACTER_OVERLAP_RATIO = 0.4
# When the top two candidates at one overlapping position are within this
# much confidence of each other, the model is not actually sure which one is
# right.  Drop that position rather than let a marginal confidence edge
# silently become a "confirmed" character.
CHARACTER_AMBIGUOUS_MARGIN = 0.20
# A character detected below CHARACTER_MODEL_MIN_CONF but at least this
# confident, sitting between two accepted characters, is treated as evidence
# that a real character was there and simply couldn't be confirmed -- rather
# than silently vanishing and shortening the assembled plate.  Below this
# floor a rejected box is treated as noise, not a missed character.
CHARACTER_GAP_MIN_CONF = 0.10

# =============================
# Backend
# =============================

API_BASE = "https://proactive-gas-station-service-kohl.vercel.app/"

# =============================
# Detection
# =============================

# A plate detector confidence below this value produced repeated detections of
# foliage and the sign frame in this camera.  OCR must never be used to decide
# whether an object is a plate; it is only used after this gate succeeds.
# The running process must be restarted after changing this value.
CONF_THRESHOLD = 0.60
# The plate model runs on the whole 1300x510 DETECTION_ROI, which Ultralytics
# letterboxes down to imgsz before inference.  At the default 640 a 50px-wide
# plate (a car still a few metres out, or one turning its rear to the camera)
# shrinks to ~25px and its confidence falls under CONF_THRESHOLD -- on this
# camera's saved frames 640 missed the plate in 6 of 13 screenshots, 960 in 1.
PLATE_MODEL_IMGSZ = 960
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
# ...unless that single frame was this confident. Waiting for a second
# agreeing hit costs at least COLOR_MODEL_MIN_INTERVAL_SEC of real time, which
# a vehicle only briefly in view (a fast car, or a short recorded clip) may
# not have -- it leaves with no entry at all rather than a slightly-delayed
# one. A read this far above the ordinary per-hit floor (COLOR_MIN_CONF) is
# trusted on its own, the same way SINGLE_READ_PROMOTION_MIN_CONF already
# lets one strong plate read through without its usual second confirmation.
COLOR_SINGLE_HIT_PROMOTION_MIN_CONF = 0.70
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
# Submit at most three sharp crops per tracked vehicle.  They can be queued
# while OCR jobs are still running, which gives fast vehicles one extra chance
# to produce a matching read without repeatedly OCRing a stopped vehicle.
OCR_MAX_JOBS_PER_TRACK = 3
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
# A vehicle moving fast enough to leave before PlateStabilizer collects its
# normal second confirming read otherwise gets zero backend record at all --
# not even the [PROVISIONAL] console fallback fires until every OCR attempt
# is spent, which a fast vehicle may never reach.  Promote a single read to
# the final plate (and let it send a real entry/exit event) only when it is
# well above the ordinary OCR_MIN_CONF gate, since a lone read never gets
# the safety of a second agreeing read to catch a one-off misread.
SINGLE_READ_PROMOTION_MIN_CONF = 0.55

COOLDOWN_SEC = 5

EXIT_AFTER_SEC = 3

UPSCALE_TARGET_W = 1000

# [DETECTED] is a console summary line only -- the backend entry event fires
# independently the moment plate+colour are ready and is never delayed by
# this.  Make/model resolves on its own throttled schedule and often lands
# a beat after plate+colour, so hold the summary line for up to this long to
# give make a bounded chance to be included, instead of always printing
# "unknown" for a value that was simply about to arrive.
DETECTED_GRACE_SEC = 2.0

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
# Save the exact crop handed to brand.pt for every attempt, so a run of empty
# detections can be inspected visually instead of guessed at from logs alone.
DEBUG_MAKE_MODEL_SAVE_INPUTS = bool(os.environ.get("DEBUG_MAKE_MODEL_SAVE_INPUTS")) or DEBUG_MAKE_MODEL

ENABLE_MAKE_MODEL = bool(os.environ.get("ENABLE_MAKE_MODEL"))
MAKE_MODEL_MIN_CONF = float(os.environ.get("MAKE_MODEL_MIN_CONF", "0.55"))
# `brand.pt` identifies vehicle make; it has been both a badge/logo detector
# and a whole-image classifier at different points, and only ever reports
# the make, not the specific model.
BRAND_MODEL_PATH = "brand.pt"
# Make/model is secondary metadata, exactly like colour.  Throttle it the
# same way so a real classifier call can never compete with plate OCR for
# the GPU or stall the main video-loop thread every frame.
MAKE_MODEL_MIN_INTERVAL_SEC = 0.75
# How long an EXITING vehicle's colour/make attempt waits for a legible
# plate before giving up and guessing from whatever crop is available (see
# _attribute_ready in main.py, and ENTRY_DIRECTION_SPLIT_Y above for why
# entering traffic does not wait at all). A detected plate-shaped box on
# this vehicle (session["plate_box"]) is the same "this is genuinely a
# legible view" signal the OCR pipeline already requires, so colour/make
# leans on it too rather than firing on whatever crop happens to be
# available first -- firing immediately let two agreeing (wrong) reads,
# just 2*MAKE_MODEL_MIN_INTERVAL_SEC apart, lock the stabilizer in before
# the vehicle ever reached a clean view. Not every vehicle's plate gets a
# box at all (glare, occlusion, an angle the detector misses) --
# ATTRIBUTE_FALLBACK_SEC caps that wait so a hard case still gets one
# best-effort guess before it leaves, rather than sitting at "unknown"
# forever.
ATTRIBUTE_FALLBACK_SEC = 3.0
# A YOLO box only ever bounds the VISIBLE part of an object.  When a vehicle
# is close enough to the camera that part of it extends past the frame edge,
# the box is clipped exactly at that edge, and the crop built from it is a
# fragment -- a door panel, a taillight -- not a usable whole-vehicle view.
# This is a different failure from the plate_box wait above (that one caught
# a vehicle still turning into the driveway, fully visible but at the wrong
# angle; this one catches a vehicle that IS at a fine angle but is simply too
# close for its whole body to fit in frame) -- real examples of both showed
# up on this camera, so both checks are needed together, not one instead of
# the other. This margin is pixels in the 1500x890 processing frame, not a
# fraction of the vehicle's own box, since a frame edge is a fixed boundary
# regardless of how large or small the vehicle in front of it is.
VEHICLE_FRAME_EDGE_MARGIN = 15
# brand.pt is the fine-tuned model from ai-module/brand_dataset (11 classes,
# trained entirely on this station's own camera crops + condo phone photos
# -- CompCars was deliberately removed from the training data this time; see
# eval_brand_own_crops.py for the honest per-class accuracy this achieves --
# 93.9% (108/115) at last check, and since val is now 100% real images rather
# than CompCars-diluted, that figure is directly trustworthy, not a
# blended/inflated one). The previous CompCars-mixed fine-tune is preserved
# at ai-module/brand.pt.finetuned; the original un-fine-tuned 161-class
# model is preserved at ai-module/brand.pt.bak. Every entry here is a
# straight lowercase mapping (this model's class names are already clean),
# so the restrict+renormalize step below is effectively a no-op today --
# kept anyway so the *next* brand.pt swap fails safe instead of silently
# reporting an irrelevant class, the way an unmaintained allowlist would.
# Audi, BMW, Ford, and Zeekr have no entry -- none of them ended up with
# enough real training data to be included in this model at all. Update
# this dict's keys whenever brand.pt's own class list changes -- check with
# `YOLO('brand.pt').names` -- since a stale key here silently excludes that
# class from ever being reported, exactly as it would for this exact model
# if left unchanged.
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
# Renormalizing among only the allowed makes can manufacture false
# confidence out of noise: on a test crop with no real vehicle at all, every
# raw probability was negligible (<=0.04), yet the largest of them still
# renormalized to a much larger-looking number purely because its
# equally-meaningless neighbours were even smaller. Require the winning
# class's RAW (pre-renormalization) share of the softmax to clear this floor
# too, so a decision is only trusted when the model gave that class real
# attention to begin with. With every class now in BRAND_ALLOWLIST this
# floor applies almost directly to the model's own top1 confidence (little
# is renormalized away), so it now mainly guards against a genuinely
# uncertain, near-uniform prediction rather than the 161-class dilution
# effect it was originally added for.
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
