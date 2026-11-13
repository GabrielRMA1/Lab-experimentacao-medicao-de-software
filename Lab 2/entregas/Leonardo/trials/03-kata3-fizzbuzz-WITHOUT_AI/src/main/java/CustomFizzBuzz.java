import java.util.Map;

public class CustomFizzBuzz {
    public static String evaluate(int number, Map<Integer, String> rules) {
        String output = "";
        if (rules != null) {
            for (Integer key : rules.keySet()) {
                if (key != null && key != 0 && number % key == 0) {
                    String label = rules.get(key);
                    if (label != null) {
                        output = output + label;
                    }
                }
            }
        }
        if (output.equals("")) {
            return String.valueOf(number);
        }
        return output;
    }
}
