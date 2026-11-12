import java.util.Map;

public class CustomFizzBuzz {
    public static String evaluate(int number, Map<Integer, String> rules) {
        if (rules == null || rules.isEmpty()) {
            return Integer.toString(number);
        }
        StringBuilder token = new StringBuilder();
        for (Map.Entry<Integer, String> rule : rules.entrySet()) {
            Integer divisor = rule.getKey();
            String word = rule.getValue();
            if (divisor == null || divisor == 0 || word == null) {
                continue;
            }
            if (number % divisor == 0) {
                token.append(word);
            }
        }
        return token.length() == 0 ? Integer.toString(number) : token.toString();
    }
}
