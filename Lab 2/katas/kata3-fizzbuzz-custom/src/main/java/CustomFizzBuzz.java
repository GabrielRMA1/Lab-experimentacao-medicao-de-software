import java.util.Map;

public class CustomFizzBuzz {
    public static String evaluate(int number, Map<Integer, String> rules) {
        if (rules == null || rules.isEmpty()) {
            return String.valueOf(number);
        }

        StringBuilder result = new StringBuilder();

        for (Map.Entry<Integer, String> rule : rules.entrySet()) {
            if (rule.getKey() == null || rule.getValue() == null) {
                continue;
            }
            if (number % rule.getKey() == 0) {
                result.append(rule.getValue());
            }
        }

        return result.length() > 0 ? result.toString() : String.valueOf(number);
    }
}