package JavaExtractor.FeaturesEntities;

import com.fasterxml.jackson.annotation.JsonIgnore;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonPropertyDescription;

import java.util.ArrayList;
import java.util.function.Function;

public class ProgramRelation {
  public static Function<String, String> s_Hasher = (s) -> Integer.toString(s.hashCode());
  private String m_Source;
  private String m_Target;
  private String m_HashedPath;
  private String m_Path;
  @SuppressWarnings("FieldCanBeLocal")
  @JsonPropertyDescription
  private ArrayList<String> result;

  public ProgramRelation(String sourceName, String targetName, String path) {
    m_Source = sourceName;
    m_Target = targetName;
    m_Path = path;
    m_HashedPath = s_Hasher.apply(path);
  }

  public static void setNoHash() {
    s_Hasher = (s) -> s;
  }

  public String toString() {
    return String.format("%s,%s,%s", m_Source, m_HashedPath, m_Target);
  }

  @JsonIgnore
  public String getPath() {
    return m_Path;
  }

  @JsonIgnore
  public String getSource() {
    return m_Source;
  }

  @JsonIgnoreProperties
  public String getTarget() {
    return m_Target;
  }

  @JsonIgnore
  public String getHashedPath() {
    return m_HashedPath;
  }
}
