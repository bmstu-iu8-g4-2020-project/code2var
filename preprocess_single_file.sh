MAX_PATH_LENGTH=8
MAX_PATH_WIDTH=2
EXTRACTOR_JAR=JavaExtractor/JPredict/target/JavaExtractor-0.0.1-SNAPSHOT.jar
PYTHON=python3


FILE=$1
OUTPUT_DIR=$2

OUTPUT_FILE="$OUTPUT_DIR"/data.code2var
cd JavaExtractor/JPredict/ && mvn clean -q install && cd ../..

chmod +x JavaExtractor/extract.py
mkdir "$OUTPUT_DIR"/t/
mv "$FILE" "$OUTPUT_DIR"/t/
${PYTHON} JavaExtractor/extract.py -maxlen ${MAX_PATH_LENGTH} -maxwidth ${MAX_PATH_WIDTH} -j ${EXTRACTOR_JAR} \
  --dir "$OUTPUT_DIR"/ --obfuscate true  2>&1 | tee "$OUTPUT_DIR"/processing.log

find "$OUTPUT_DIR" -name '*.data.log' -exec cat {} > ${OUTPUT_FILE} \;

chmod +x preprocess.py

${PYTHON} preprocess.py --data_dir ${OUTPUT_DIR} --combined_file ${OUTPUT_FILE} --max_contexts 300 \
  --output_name ${OUTPUT_DIR}/data --net vec --occurrences 0 --min_folders 0
