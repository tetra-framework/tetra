# Default settings for Tetra

TETRA_FILE_CACHE_DIR_NAME = "__tetracache__"
TETRA_ESBUILD_JS_ARGS = [
    "--bundle",
    "--minify",
    "--sourcemap",
    "--entry-names=[name]-[hash]",
    "--target=chrome80,firefox73,safari13,edge80",
]
TETRA_ESBUILD_CSS_ARGS = [
    "--bundle",
    "--minify",
    "--sourcemap",
    "--entry-names=[name]-[hash]",
    "--loader:.png=file",
    "--loader:.svg=file",
    "--loader:.gif=file",
    "--loader:.jpg=file",
    "--loader:.jpeg=file",
    "--loader:.webm=file",
    "--loader:.woff=file",
    "--loader:.woff2=file",
    "--loader:.ttf=file",
]

TETRA_TEMP_UPLOAD_PATH = "tetra_temp_upload"
