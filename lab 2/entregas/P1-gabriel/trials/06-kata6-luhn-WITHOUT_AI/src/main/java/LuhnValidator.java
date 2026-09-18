public class LuhnValidator {
    public static boolean isValid(String cardNumber) {
        if (cardNumber == null) {
            return false;
        }

        String digits = "";
        for (int i = 0; i < cardNumber.length(); i++) {
            char c = cardNumber.charAt(i);
            if (c == ' ') {
                continue;
            }
            if (c < '0' || c > '9') {
                return false;
            }
            digits += c;
        }

        if (digits.isEmpty()) {
            return false;
        }

        int sum = 0;
        boolean doubleIt = false;
        for (int i = digits.length() - 1; i >= 0; i--) {
            int n = digits.charAt(i) - '0';
            if (doubleIt) {
                n = n * 2;
                if (n > 9) {
                    n = n - 9;
                }
            }
            sum += n;
            doubleIt = !doubleIt;
        }
        return sum % 10 == 0;
    }
}
