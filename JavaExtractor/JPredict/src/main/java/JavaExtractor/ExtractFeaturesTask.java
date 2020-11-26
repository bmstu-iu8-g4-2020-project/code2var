package JavaExtractor;

import JavaExtractor.Common.CommandLineValues;
import JavaExtractor.Common.Common;
import JavaExtractor.FeaturesEntities.ProgramFeatures;
import com.github.javaparser.ParseException;
import org.apache.commons.lang3.StringUtils;
import spoon.Launcher;
import spoon.SpoonException;
import spoon.refactoring.CtRenameGenericVariableRefactoring;
import spoon.reflect.code.CtLiteral;
import spoon.reflect.declaration.*;
import spoon.support.compiler.VirtualFile;
import spoon.support.reflect.reference.CtExecutableReferenceImpl;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collection;
import java.util.HashMap;
import java.util.List;
import java.util.stream.Collectors;
import java.util.stream.IntStream;

public class ExtractFeaturesTask implements Runnable {
  private static final int MAX_VAR_NUMBERS = 25;
  private static final Integer MAX_FUNC_NUMBERS = 100;
  CommandLineValues m_CommandLineValues;
  Path filePath;
  String code;

  HashMap<String, HashMap<String, String>> obfuscatedNames;
  ArrayList<Integer> freeIndexes;
  Integer freeIndexesNumber;

  public ExtractFeaturesTask(CommandLineValues commandLineValues, Path path) {
    m_CommandLineValues = commandLineValues;
    this.filePath = path;
    try {
      code = new String(Files.readAllBytes(this.filePath));
    } catch (IOException e) {
      e.printStackTrace();
      code = Common.EmptyString;
    }
    obfuscatedNames = new HashMap<>();
  }

  @Override
  public void run() {
    try {
      if (m_CommandLineValues.Obfuscate) {
        obfuscateCode();
      }
      processFile();

    } catch (Exception e) {
      e.printStackTrace();
    }
  }

  public void obfuscateCode() {
    try {
      Collection<CtType<?>> allTypes = returnAllTypes(code);

      StringBuilder stringBuilder = new StringBuilder();

      for (CtType<?> classOrInterface : allTypes) {
        String obfuscated = obfuscateToCtClass((CtClass<?>) classOrInterface).toString();

        if (!obfuscated.equals("")) {
          stringBuilder.append(obfuscated).append("\n\n");
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
        List<CtElement> el = method.getElements(ctElement -> true);
        freeIndexes =
            (ArrayList<Integer>)
                IntStream.rangeClosed(0, MAX_VAR_NUMBERS - 1).boxed().collect(Collectors.toList());
        freeIndexesNumber = MAX_VAR_NUMBERS;

        method
            .getElements(
                element ->
                    element.getClass() == spoon.support.reflect.declaration.CtParameterImpl.class)
            .forEach(
                parameter -> {
                  CtParameter param = (CtParameter) parameter;
                  obfuscateVariable(method, param);
                });

        method
            .getElements(
                element ->
                    element.getClass() == spoon.support.reflect.code.CtLocalVariableImpl.class)
            .forEach(
                variable -> {
                  CtVariable var = (CtVariable) variable;
                  obfuscateVariable(method, var);
                });

        freeIndexes =
            (ArrayList<Integer>)
                IntStream.rangeClosed(0, MAX_FUNC_NUMBERS - 1).boxed().collect(Collectors.toList());
        freeIndexesNumber = MAX_FUNC_NUMBERS;

        method
            .getElements(element -> element.getClass() == CtExecutableReferenceImpl.class)
            .forEach(
                function -> {
                  CtExecutableReferenceImpl func = (CtExecutableReferenceImpl) function;
                  obfuscateExecutableReference(method, func);
                });
        method
            .getElements(
                element -> element.getClass() == spoon.support.reflect.code.CtLiteralImpl.class)
            .forEach(
                element -> {
                  CtLiteral literal = (CtLiteral) element;
                  if (literal.getValue() == null) {
                    literal.setValue("NULL");
                  } else if (!(literal.getValue().equals(1)
                      || literal.getValue().equals(0)
                      || literal.getValue().equals(Integer.MAX_VALUE)
                      || literal.getValue().equals(Float.NaN)
                      || literal.getValue().equals(Common.EmptyString))) {
                    literal.setValue("CONSTANT");
                  } else {
                    System.err.println(literal.getValue());
                  }
                });
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

  private void obfuscateExecutableReference(CtMethod method, CtExecutableReferenceImpl func) {
    if (func == null) {
      return;
    }

    if (!obfuscatedNames.containsKey(method.getSimpleName())) {
      obfuscatedNames.put(method.getSimpleName(), new HashMap<>());
    }

    String newName = generateName("FUNC_");
    obfuscatedNames.get(method.getSimpleName()).put(newName, func.getSimpleName());
    func.setSimpleName(newName);
  }

  private void obfuscateVariable(CtMethod method, CtVariable var) {
    if (var == null || var.getType() == null) {
      return;
    }
    if (!obfuscatedNames.containsKey(method.getSimpleName())) {
      obfuscatedNames.put(method.getSimpleName(), new HashMap<>());
    }

    String newName = generateName("VARIABLE_");
    obfuscatedNames.get(method.getSimpleName()).put(newName, var.getSimpleName());
    new CtRenameGenericVariableRefactoring().setTarget(var).setNewName(newName).refactor();
  }

  private String generateName(String prefix) {
    if (freeIndexesNumber == 0) {
      throw new RuntimeException("Too many different objects for prefix." + prefix);
    }
    StringBuilder stringBuilder = new StringBuilder();
    stringBuilder.append(prefix);
    int varIdx = (int) (Math.random() * freeIndexesNumber);
    stringBuilder.append(freeIndexes.get(varIdx));
    freeIndexes.remove(varIdx);
    freeIndexesNumber--;
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

    if (m_CommandLineValues.OnlyVars) {
      for (ProgramFeatures feature : features) {
        String originalName = feature.getName();
        if (m_CommandLineValues.Obfuscate
            && obfuscatedNames.get(feature.getMethodName()) != null
            && obfuscatedNames.get(feature.getMethodName()).get(originalName) != null) {
          feature.setName(obfuscatedNames.get(feature.getMethodName()).get(originalName));
        }
        ArrayList<String> splitNameParts = Common.splitToSubtokens(feature.getName());
        String splitName = feature.getName();
        if (splitNameParts.size() > 0) {
          splitName = splitNameParts.stream().collect(Collectors.joining(Common.internalSeparator));
        }
        feature.setName(splitName);
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

      String toPrint = singleMethodfeatures.toString();
      if (m_CommandLineValues.PrettyPrint) {
        toPrint = toPrint.replace(" ", "\n\t");
      }
      builder.append(toPrint);

      methodsOutputs.add(builder.toString());
    }
    return StringUtils.join(methodsOutputs, "\n");
  }

  public String filename() {
    return filePath.toString();
  }
}
