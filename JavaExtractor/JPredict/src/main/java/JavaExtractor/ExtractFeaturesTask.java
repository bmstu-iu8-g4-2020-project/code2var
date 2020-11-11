package JavaExtractor;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collection;
import java.util.HashMap;
import java.util.List;
import java.util.concurrent.Callable;

import org.apache.commons.lang3.StringUtils;

import com.github.javaparser.ParseException;

import JavaExtractor.Common.CommandLineValues;
import JavaExtractor.Common.Common;
import JavaExtractor.FeaturesEntities.ProgramFeatures;
import spoon.Launcher;
import spoon.SpoonException;
import spoon.refactoring.CtRenameGenericVariableRefactoring;
import spoon.reflect.declaration.*;
import spoon.support.compiler.VirtualFile;

public class ExtractFeaturesTask implements Callable<Void> {
    CommandLineValues m_CommandLineValues;
    Path filePath;
    String code = null;

    HashMap<String, String> obfuscatedNames;

    public ExtractFeaturesTask(CommandLineValues commandLineValues, Path path) {
        m_CommandLineValues = commandLineValues;
        this.filePath = path;
        try {
            code = new String(Files.readAllBytes(this.filePath));
        } catch (IOException e) {
            e.printStackTrace();
            code = Common.EmptyString;
        }
        obfuscatedNames = new HashMap<String, String>();
    }

    @Override
    public Void call() throws Exception {
        System.err.println("Extracting file: " + filePath);
        if (m_CommandLineValues.Obfuscate){
            obfuscateCode();
        }
        processFile();
        System.err.println("Done with file: " + filePath);
        return null;
    }

    public void obfuscateCode() {
        try {
            Collection<CtType<?>> allTypes = returnAllTypes(code);

            StringBuilder stringBuilder = new StringBuilder();

            for (CtType classOrInterface : allTypes) {
                try {
                    String obfuscated = obfuscateToCtClass((CtClass<?>) classOrInterface).toString();

                    if (!obfuscated.equals("")) {
                        stringBuilder.append(obfuscated).append("\n\n");
                    }
                } catch (ClassCastException e) {
//                System.out.println("Сouldn't cast to class, might be interface");
                }
            }
            code = stringBuilder.append("\n\n").toString();
        } catch (Exception e) {
//            System.out.println("Ignored: " + e.getMessage());
        }

    }

    private CtClass obfuscateToCtClass(CtClass newClass) {
        try {
            for (Object oMethod : newClass.getMethods()) {
                CtMethod method = (CtMethod) oMethod;

                method.getElements(element ->
                        element.getClass() == spoon.support.reflect.declaration.CtParameterImpl.class
                ).forEach(parameter -> {
                    CtParameter param = (CtParameter) parameter;
                    obfuscateVariable(param);
                });

                method.getElements(element -> element.getClass() == spoon.support.reflect.code.CtLocalVariableImpl.class
                ).forEach(
                        variable -> {
                            CtVariable var = (CtVariable) variable;
                            obfuscateVariable(var);
                        }
                );
            }
            return newClass;
        } catch (SpoonException e) {
            System.err.println("\tFile:\t" + filePath.toString() + "\t" + e);
            return null;
        } catch (Exception e) {
            System.err.print(filePath.toString() + " - ");
            e.printStackTrace();
            return null;
        }
    }

    private void obfuscateVariable(CtVariable var) {
        if (var == null || var.getType() == null) {
            return;
        }
        String newName = generateName(12);
        obfuscatedNames.put(newName, var.getSimpleName());
        new CtRenameGenericVariableRefactoring().setTarget(var).setNewName(newName).refactor();
    }

    private String generateName(int length) {
        StringBuilder stringBuilder = new StringBuilder();
        for (int i = 0; i < length; i++) {
            stringBuilder.append((char) ('a' + (int) (Math.random() * 26)));
        }
        return stringBuilder.toString();
    }


    private Collection<CtType<?>> returnAllTypes(String code) {
        Launcher launcher = new Launcher();
        launcher.addInputResource(new VirtualFile(code));
        launcher.getEnvironment().setNoClasspath(true);
        launcher.getEnvironment().setAutoImports(true);
        return launcher.buildModel().getAllTypes();

    }

    public void processFile() {
        ArrayList<ProgramFeatures> features;
        try {
            features = extractSingleFile();
        } catch (ParseException | IOException e) {
            e.printStackTrace();
            return;
        }
        if (features == null) {
            return;
        }

        String toPrint = featuresToString(features);
        if (toPrint.length() > 0) {
            System.out.println(toPrint);
        }
    }

    public ArrayList<ProgramFeatures> extractSingleFile() throws ParseException, IOException {
        FeatureExtractor featureExtractor = new FeatureExtractor(m_CommandLineValues);

        ArrayList<ProgramFeatures> features = featureExtractor.extractFeatures(code);
        if (m_CommandLineValues.OnlyVars && m_CommandLineValues.Obfuscate){
            for (ProgramFeatures feature: features){
                feature.setName(obfuscatedNames.get(feature.getName()));
            }
        }
        return features;
    }

    public String featuresToString(ArrayList<ProgramFeatures> features) {
        if (features == null || features.isEmpty()) {
            return Common.EmptyString;
        }

        List<String> methodsOutputs = new ArrayList<>();

        for (ProgramFeatures singleMethodfeatures : features) {
            StringBuilder builder = new StringBuilder();

            String toPrint = Common.EmptyString;
            toPrint = singleMethodfeatures.toString();
            if (m_CommandLineValues.PrettyPrint) {
                toPrint = toPrint.replace(" ", "\n\t");
            }
            builder.append(toPrint);


            methodsOutputs.add(builder.toString());

        }
        return StringUtils.join(methodsOutputs, "\n");
    }

    public String filename(){
        return filePath.toString();
    }

}
