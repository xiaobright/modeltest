import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

HTTP_HOST = os.getenv('HTTP_HOST', '0.0.0.0')
HTTP_PORT = int(os.getenv('HTTP_PORT', '8765'))
LOCATION = os.getenv('LOCATION_NAME', 'default')

ADMIN_AUTH_ENABLED = os.getenv('ADMIN_AUTH_ENABLED', '1') not in ('0', 'false', 'False')
ADMIN_SESSION_COOKIE = os.getenv('ADMIN_SESSION_COOKIE', 'project2_admin')
ADMIN_SESSION_TTL_MS = max(10 * 60 * 1000, int(os.getenv('ADMIN_SESSION_TTL_MS', str(8 * 60 * 60 * 1000))))
ADMIN_PASSWORD_MIN_LEN = max(8, int(os.getenv('ADMIN_PASSWORD_MIN_LEN', '8')))
MAX_JSON_BODY_BYTES = max(1024, int(os.getenv('MAX_JSON_BODY_BYTES', str(8 * 1024 * 1024))))

SLEEP_OUTPUT_DIR = os.path.abspath(
    os.getenv('SLEEP_OUTPUT_DIR', os.path.join(os.path.dirname(__file__), '..', 'sleep_deploy_pack', 'examples'))
)
SLEEP_EPOCH_FILE = os.path.abspath(os.getenv('SLEEP_EPOCH_FILE', os.path.join(SLEEP_OUTPUT_DIR, 'fusion_eeg_final_conf.csv')))
SLEEP_QUALITY_FILE = os.path.abspath(os.getenv('SLEEP_QUALITY_FILE', os.path.join(SLEEP_OUTPUT_DIR, 'sleep_quality_per_record.csv')))
SLEEP_IMPORT_INTERVAL_S = max(3, int(os.getenv('SLEEP_IMPORT_INTERVAL_S', '10')))
SLEEP_IMPORT_ENABLED = os.getenv('SLEEP_IMPORT_ENABLED', '1') not in ('0', 'false', 'False')
SLEEP_IMPORT_DEFAULT_ROOM = os.getenv('SLEEP_IMPORT_DEFAULT_ROOM', '').strip()
SLEEP_IMPORT_DEFAULT_BED = os.getenv('SLEEP_IMPORT_DEFAULT_BED', '').strip()
SLEEP_IMPORT_UNSCOPED_POLICY = os.getenv('SLEEP_IMPORT_UNSCOPED_POLICY', 'first').strip().lower()
if SLEEP_IMPORT_UNSCOPED_POLICY not in ('first', 'skip', 'all'):
    SLEEP_IMPORT_UNSCOPED_POLICY = 'first'

DASHBOARD_FILE = os.path.join(os.path.dirname(__file__), 'dashboard.html')
ADMIN_FILE = os.path.join(os.path.dirname(__file__), 'admin.html')
DATA_DIR = os.path.abspath(os.getenv('PROJECT2_DATA_DIR', os.path.join(os.path.dirname(__file__), '..', 'data')))
DB_FILE = os.path.abspath(os.getenv('PROJECT2_DB_FILE', os.path.join(DATA_DIR, 'project2.db')))
DEFAULT_ADMIN_SUBJECT_ID = os.getenv('DEFAULT_ADMIN_SUBJECT_ID', 'sub_admin_default')
DEFAULT_ADMIN_NAME = os.getenv('DEFAULT_ADMIN_NAME', '超级管理员')
SESSION_TTL_MS = max(10_000, int(os.getenv('SESSION_TTL_MS', '120000')))
FACE_DETECTOR_MODEL = os.path.abspath(os.getenv(
    'FACE_DETECTOR_MODEL',
    os.path.join(PROJECT_ROOT, 'vision', 'models', 'face_detection_yunet_2023mar.onnx'),
))
FACE_ENROLL_DETECT = os.getenv('FACE_ENROLL_DETECT', '1') not in ('0', 'false', 'False')
FACE_DETECT_SCORE_THRESHOLD = float(os.getenv('FACE_DETECT_SCORE_THRESHOLD', '0.75'))
FACE_MATCH_RECOGNIZED_THRESHOLD = float(os.getenv('FACE_MATCH_RECOGNIZED_THRESHOLD', '0.82'))
FACE_MATCH_CANDIDATE_THRESHOLD = float(os.getenv('FACE_MATCH_CANDIDATE_THRESHOLD', '0.72'))

HISTORY_MINUTES = int(os.getenv('HISTORY_MINUTES', '30'))
HISTORY_TTL_MS = HISTORY_MINUTES * 60 * 1000
KIND_TTL_MS = {
    'sleep_epoch': 48 * 60 * 60 * 1000,
    'sleep_quality': 7 * 24 * 60 * 60 * 1000,
    'posture': 2 * 60 * 60 * 1000,
}
ESP_SET_TIMEOUT_MS = int(os.getenv('ESP_SET_TIMEOUT_MS', '2000'))
ESP_STORE_DEPTH = max(1, int(os.getenv('ESP_STORE_DEPTH', '1')))
ESP_REQUIRED_STREAMS = ('mlx1', 'mlx2', 'tof1', 'tof2')
ESP_ONLINE_TTL_MS = int(os.getenv('ESP_ONLINE_TTL_MS', '15000'))

POSTURE_CLASS_NAMES = ['仰卧(Supine)', '侧卧(Lateral)', '俯卧(Prone)']
EMOTION_LABELS = ['愤怒', '蔑视', '厌恶', '恐惧', '开心', '自然', '悲伤', '惊讶']
EMOTION_CONTEXT_TTL_MS = max(5000, int(os.getenv('EMOTION_CONTEXT_TTL_MS', '15000')))
