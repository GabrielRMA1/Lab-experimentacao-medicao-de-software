public class LuhnValidator {
    public static boolean isValid(String cardNumber) {
        String digits = onlyDigits(cardNumber);
        if (digits == null || digits.length() == 0) {
            return false;
        }
        return checksum(digits) % 10 == 0;
    }

    private static String onlyDigits(String cardNumber) {
        if (cardNumber == null) {
            return null;
        }
        StringBuilder digits = new StringBuilder();
        for (int i = 0; i < cardNumber.length(); i++) {
            char c = cardNumber.charAt(i);
            if (c == ' ' || c == '-') {
                continue;
            }
            if (!Character.isDigit(c)) {
                return null;
            }
            digits.append(c);
        }
        return digits.toString();
    }

    private static int checksum(String digits) {
        int total = 0;
        int positionFromRight = 0;
        for (int i = digits.length() - 1; i >= 0; i--) {
            int digit = digits.charAt(i) - '0';
            if (positionFromRight % 2 == 1) {
                digit = doubleAndReduce(digit);
            }
            total += digit;
            positionFromRight++;
        }
        return total;
    }

    private static int doubleAndReduce(int digit) {
        int doubled = digit * 2;
        if (doubled >= 10) {
            return doubled - 9;
        }
        return doubled;
    }
}
