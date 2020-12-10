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
  List<List<String>> predicions;

  public FileDeobfuscator(CommandLineValues commandLineValues, File file) {
    this.filePath = file;
    m_CommandLineValues = commandLineValues;

    try {
      code = new String(FileUtils.readFileToByteArray(this.filePath));
      predicions = generatePredictions();
    } catch (IOException e) {
      e.printStackTrace();
      code = Common.EmptyString;
    }
  }

  private List<List<String>> generatePredictions() {
    List<List<String>> data = new ArrayList<>();
    try (BufferedReader br =
        new BufferedReader(new FileReader("tmp_data_for_code2var/result.csv"))) {
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
        System.out.println("Created file "+ classOrInterface.getSimpleName() + "-deobfuscated.java");
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
    int idx = 0;
    for (MethodContent omethod : orderedMethods) {
      Set<String> usedNames = new HashSet<>();
      System.out.println("Before:");
      System.out.println(map.get(omethod.getMethodName()).prettyprint());
      System.out.println("After:");
      CtMethod deobfuscated = map.get(omethod.getMethodName());
      int new_idx = changeAll(deobfuscated, usedNames, idx);
      System.out.println(deobfuscated.prettyprint());
      System.out.println(
          "If you want to view options for variable, enter it's name from \"After\" part. If you satisfied with deobfuscation, press Enter.");
           String input = System.console().readLine();
           while (!input.equals("")) {
             changeOne(deobfuscated, input, usedNames, idx);
             System.out.println(
                 "If you want to view options for variable, enter it's name from \"After\" part. If you satisfied with deobfuscation, press Enter.");
             input = System.console().readLine();
           }
      idx = new_idx;
    }
  }

  private void changeOne(CtMethod method, String change, Set<String> usedNames, int idx) {
    for (Object parameter :
        method.getElements(
            element ->
                element.getClass() == spoon.support.reflect.declaration.CtParameterImpl.class)) {
      CtParameter param = (CtParameter) parameter;
      if (param.getSimpleName().equals(change)) {
        String changeTo = createNewName(change, idx);
        usedNames.remove(change);
        new CtRenameGenericVariableRefactoring()
            .setTarget(param)
            .setNewName(generateName(usedNames, changeTo))
            .refactor();
      }
      idx++;
    }
    for (Object variable :
        method.getElements(
            element ->
                element.getClass() == spoon.support.reflect.code.CtLocalVariableImpl.class
                    || element.getClass()
                        == spoon.support.reflect.code.CtCatchVariableImpl.class)) {
      CtVariable var = (CtVariable) variable;

      if (var.getSimpleName().equals(change)) {
        String changeTo = createNewName(change, idx);
        usedNames.remove(change);
        new CtRenameGenericVariableRefactoring()
            .setTarget(var)
            .setNewName(generateName(usedNames, changeTo))
            .refactor();
      }
      idx++;
    }
    System.out.println(method.prettyprint());
  }

  private String createNewName(String old, int idx) {
    String newName;
    System.out.println(
        "Choose one of this (write down number from 0 to 5) ["
            + String.join(" ", predicions.get(idx))
            + "] or type your variant:");
    String input = System.console().readLine();
    if (input.matches("[0-9]")) {
      int choice = Integer.parseInt(input);
      if (choice < predicions.get(idx).size()) {
        newName = predicions.get(idx).get(choice);
      } else {
        System.out.println("You entered wrong number. Correct number should be between 0 and 5.");
        newName = old;
      }
    } else {
      newName = input;
    }
    return newName;
  }

  private int changeAll(CtMethod method, Set<String> usedNames, int idx) {
    for (Object parameter :
        method.getElements(
            element ->
                element.getClass() == spoon.support.reflect.declaration.CtParameterImpl.class)) {
      CtParameter param = (CtParameter) parameter;
      List<String> possibleNames = predicions.get(idx);
      idx++;
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
      List<String> possibleNames = predicions.get(idx);
      idx++;
      new CtRenameGenericVariableRefactoring()
          .setTarget(var)
          .setNewName(generateName(usedNames, possibleNames.get(1)))
          .refactor();
    }
    return idx;
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
