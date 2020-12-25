package JavaExtractor;

import JavaExtractor.Common.CommandLineValues;
import JavaExtractor.Common.Common;
import JavaExtractor.Common.MethodContent;
import org.apache.commons.io.FileUtils;
import org.apache.commons.lang3.NotImplementedException;
import spoon.refactoring.CtRenameGenericVariableRefactoring;
import spoon.reflect.declaration.*;

import java.io.*;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class FileDeobfuscator {
  CommandLineValues m_CommandLineValues;
  File filePath;
  String code;
  List<List<String>> vecPredicions;
  List<List<String>> varPredicions;

  public FileDeobfuscator(CommandLineValues commandLineValues, File file) {
    this.filePath = file;
    m_CommandLineValues = commandLineValues;

    try {
      code = new String(FileUtils.readFileToByteArray(this.filePath));
      vecPredicions = generatePredictions("tmp_data_for_code2var/result.vec.csv");
      varPredicions = generatePredictions("tmp_data_for_code2var/result.var.csv");
    } catch (IOException e) {
      e.printStackTrace();
      code = Common.EmptyString;
    }
  }

  private List<List<String>> generatePredictions(String filename) {
    List<List<String>> data = new ArrayList<>();
    try (BufferedReader br = new BufferedReader(new FileReader(filename))) {
      String line;
      while ((line = br.readLine()) != null) {
        String[] values = line.split(",");
        data.add(Arrays.asList(values.clone()));
      }
    } catch (IOException e) {
      e.printStackTrace();
    }
    return data;
  }

  public void deobfuscate() {

    try {
      Collection<CtType<?>> allTypes = ExtractFeaturesTask.returnAllTypes(code);

      StringBuilder stringBuilder = new StringBuilder();

      for (CtType<?> classOrInterface : allTypes) {
        Set<CtType<?>> a = classOrInterface.getNestedTypes();
        if (a.size() != 0) {
          throw new NotImplementedException(
              "Now we can't parse class with classes inside." + filePath);
        }
        deobfuscateToCtClass((CtClass<?>) classOrInterface);
        BufferedWriter writer =
            new BufferedWriter(
                new FileWriter(classOrInterface.getSimpleName() + "-deobfuscated.java"));
        writer.write(((CtClass<?>) classOrInterface).prettyprint());
        writer.close();
        System.out.println(
            "Created file " + classOrInterface.getSimpleName() + "-deobfuscated.java");
      }
    } catch (Exception e) {
      e.printStackTrace();
    }
  }

  private void deobfuscateToCtClass(CtClass newClass) throws IOException {
    HashMap<String, CtMethod<?>> map = new HashMap<>();
    for (Object o : newClass.getMethods()) {
      CtMethod method = (CtMethod) o;
      map.put(method.getSimpleName(), method);
    }

    ArrayList<MethodContent> orderedMethods = FeatureExtractor.extractMethods(code);
    int varIdx = 0;
    int methodIdx = 0;
    for (MethodContent omethod : orderedMethods) {
      Set<String> usedNames = new HashSet<>();
      System.out.println("Before:");
      System.out.println(map.get(omethod.getMethodName()).prettyprint());
      System.out.println("After:");
      CtMethod deobfuscated = map.get(omethod.getMethodName());
      int new_idx = changeAll(deobfuscated, usedNames, methodIdx, varIdx);
      System.out.println(deobfuscated.prettyprint());
      System.out.println(
          "If you want to view options for variable, enter it's name from \"After\" part. If you satisfied with deobfuscation, press Enter.");
      String input = System.console().readLine();
      while (!input.equals("")) {
        changeOne(deobfuscated, input, usedNames, methodIdx,
                varIdx);
        System.out.println(
            "If you want to view options for variable, enter it's name from \"After\" part. If you satisfied with deobfuscation, press Enter.");
        input = System.console().readLine();
      }
      varIdx = new_idx;
      ++methodIdx;
    }
  }

  private void changeOne(CtMethod method, String change, Set<String> usedNames, int methodIdx, int varIdx) {
    if (method.getSimpleName().equals(change)){
      String changeTo = createNewName(change, vecPredicions, methodIdx);
      usedNames.remove(change);
      spoon.refactoring.Refactoring.changeMethodName(method, changeTo);

    }
    for (Object parameter :
        method.getElements(
            element ->
                element.getClass() == spoon.support.reflect.declaration.CtParameterImpl.class)) {
      CtParameter param = (CtParameter) parameter;
      if (param.getSimpleName().equals(change)) {
        String changeTo = createNewName(change, varPredicions, varIdx);
        usedNames.remove(change);
        new CtRenameGenericVariableRefactoring()
            .setTarget(param)
            .setNewName(generateName(usedNames, changeTo))
            .refactor();
      }
      varIdx++;
    }
    for (Object variable :
        method.getElements(
            element ->
                element.getClass() == spoon.support.reflect.code.CtLocalVariableImpl.class
                    || element.getClass()
                        == spoon.support.reflect.code.CtCatchVariableImpl.class)) {
      CtVariable var = (CtVariable) variable;

      if (var.getSimpleName().equals(change)) {
        String changeTo = createNewName(change, varPredicions, varIdx);
        usedNames.remove(change);
        new CtRenameGenericVariableRefactoring()
            .setTarget(var)
            .setNewName(generateName(usedNames, changeTo))
            .refactor();
      }
      varIdx++;
    }
    System.out.println(method.prettyprint());
  }

  private String createNewName(String old, List<List<String>> predictions, int idx) {
    String newName;
    System.out.println(
        "Choose one of this (write down number from 0 to 5) ["
            + String.join(" ", predictions.get(idx))
            + "] or type your variant:");
    String input = System.console().readLine();
    if (input.matches("[0-9]")) {
      int choice = Integer.parseInt(input);
      if (choice < predictions.get(idx).size()) {
        newName = predictions.get(idx).get(choice);
      } else {
        System.out.println("You entered wrong number. Correct number should be between 0 and 5.");
        newName = old;
      }
    } else {
      newName = input;
    }
    return newName;
  }

  private int changeAll(CtMethod method, Set<String> usedNames, int methodIdx, int varIdx) {
    spoon.refactoring.Refactoring.changeMethodName(method, vecPredicions.get(methodIdx).get(1));
    for (Object parameter :
        method.getElements(
            element ->
                element.getClass() == spoon.support.reflect.declaration.CtParameterImpl.class)) {
      CtParameter param = (CtParameter) parameter;
      List<String> possibleNames = varPredicions.get(varIdx);
      varIdx++;
      new CtRenameGenericVariableRefactoring()
          .setTarget(param)
          .setNewName(generateName(usedNames, possibleNames.get(1)))
          .refactor();
    }

    for (Object variable :
        method.getElements(
            element ->
                element.getClass() == spoon.support.reflect.code.CtLocalVariableImpl.class
                    || element.getClass()
                        == spoon.support.reflect.code.CtCatchVariableImpl.class)) {

      CtVariable var = (CtVariable) variable;
      List<String> possibleNames = varPredicions.get(varIdx);
      varIdx++;
      new CtRenameGenericVariableRefactoring()
          .setTarget(var)
          .setNewName(generateName(usedNames, possibleNames.get(1)))
          .refactor();
    }
    return varIdx;
  }

  String generateName(Set<String> usedNames, String suggestedName) {
    if (!usedNames.contains(suggestedName)) {
      usedNames.add(suggestedName);
      return suggestedName;
    }
    if (!suggestedName.matches("\\*[0-9]")) {
      String name = suggestedName + "1";
      usedNames.add(name);
      return name;
    } else {
      Pattern p = Pattern.compile("\\d+");
      Matcher m = p.matcher(suggestedName);
      String name = suggestedName + (Integer.parseInt(m.group()) + 1);
      usedNames.add(name);
      return name;
    }
  }
}
