public class StringCalculator {
    public static int add(String numbers) {
        if (numbers == null || numbers.isEmpty()) {
            return 0;
        }

        String payload = numbers;
        String splitRegex = ",|\n";

        if (payload.startsWith("//")) {
            int breakLine = payload.indexOf('\n');
            String delimiter = payload.substring(2, breakLine);
            payload = payload.substring(breakLine + 1);
            splitRegex = java.util.regex.Pattern.quote(delimiter);
        }

        String[] parts = payload.split(splitRegex);
        int total = 0;
        String negatives = "";

        for (int i = 0; i < parts.length; i++) {
            if (parts[i].isEmpty()) {
                continue;
            }
            int value = Integer.parseInt(parts[i].trim());
            if (value < 0) {
                if (!negatives.isEmpty()) {
                    negatives += ",";
                }
                negatives += value;
            } else {
                total += value;
            }
        }

        if (!negatives.isEmpty()) {
            throw new IllegalArgumentException("Negatives not allowed: " + negatives);
        }
        return total;
    }
}
