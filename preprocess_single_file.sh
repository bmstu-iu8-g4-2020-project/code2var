

MAX_PATH_LENGTH=8
MAX_PATH_WIDTH=2
EXTRACTOR_JAR=JavaExtractor/JPredict/target/JavaExtractor-0.0.1-SNAPSHOT.jar
PYTHON=python3


FILE=$1
OUTPUT_DIR=$2
cd JavaExtractor/JPredict/ && mvn clean -q install && cd ../..

chmod +x JavaExtractor/extract.py
mkdir "$OUTPUT_DIR"/t/
mv "$FILE" "$OUTPUT_DIR"/t/
${PYTHON} JavaExtractor/extract.py -maxlen ${MAX_PATH_LENGTH} -maxwidth ${MAX_PATH_WIDTH} -j ${EXTRACTOR_JAR} \
  --dir "$OUTPUT_DIR"/ --only_for_vars true 2>&1 | tee "$OUTPUT_DIR"/processing.log

find "$OUTPUT_DIR" -name '*.data.log' -exec cat {} > "$OUTPUT_DIR"/data.code2var \;

chmod +x preprocess.py

${PYTHON} preprocess.py --test_data_var "$OUTPUT_DIR"/data.code2var \
  --word_histogram_var dataset/java-small/java-small.train.leaves.vocab \
  --path_histogram_var dataset/java-small/java-small.train.path.vocab \
  --target_histogram_train_var dataset/java-small/java-small.train.variables.vocab  \
  --output_name "$OUTPUT_DIR"/data --net code2var --single_dataset true
