public class StringCalculator {
    public static int add(String numbers) {
        if (isBlank(numbers)) {
            return 0;
        }

        DelimiterAndBody parsed = extractDelimiter(numbers);
        int[] values = toInts(parsed.body, parsed.delimiter);
        assertNoNegatives(values);
        return sum(values);
    }

    private static boolean isBlank(String numbers) {
        return numbers == null || numbers.length() == 0;
    }

    private static DelimiterAndBody extractDelimiter(String numbers) {
        if (!numbers.startsWith("//")) {
            return new DelimiterAndBody(",|\n", numbers);
        }
        int pos = numbers.indexOf("\n");
        String delimiter = numbers.substring(2, pos);
        String body = numbers.substring(pos + 1);
        return new DelimiterAndBody(java.util.regex.Pattern.quote(delimiter), body);
    }

    private static int[] toInts(String body, String delimiter) {
        String[] tokens = body.split(delimiter);
        int[] values = new int[tokens.length];
        int count = 0;
        for (int i = 0; i < tokens.length; i++) {
            if (tokens[i] == null || tokens[i].length() == 0) {
                continue;
            }
            values[count] = Integer.parseInt(tokens[i].trim());
            count++;
        }
        int[] compact = new int[count];
        for (int i = 0; i < count; i++) {
            compact[i] = values[i];
        }
        return compact;
    }

    private static void assertNoNegatives(int[] values) {
        String message = "";
        for (int i = 0; i < values.length; i++) {
            if (values[i] < 0) {
                if (message.length() == 0) {
                    message = "" + values[i];
                } else {
                    message = message + "," + values[i];
                }
            }
        }
        if (message.length() > 0) {
            throw new IllegalArgumentException("Negatives not allowed: [" + message + "]");
        }
    }

    private static int sum(int[] values) {
        int total = 0;
        for (int i = 0; i < values.length; i++) {
            total = total + values[i];
        }
        return total;
    }

    private static class DelimiterAndBody {
        private final String delimiter;
        private final String body;

        private DelimiterAndBody(String delimiter, String body) {
            this.delimiter = delimiter;
            this.body = body;
        }
    }
}
