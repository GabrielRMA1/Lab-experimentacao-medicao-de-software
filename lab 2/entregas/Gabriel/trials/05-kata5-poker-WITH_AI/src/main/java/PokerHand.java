import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;

public class PokerHand {
    public static String evaluate(String[] cards) {
        if (cards == null || cards.length != 5) {
            throw new IllegalArgumentException("Mão deve ter 5 cartas");
        }

        int[] ranks = new int[5];
        char[] suits = new char[5];
        Map<Integer, Integer> freq = new HashMap<>();

        for (int i = 0; i < 5; i++) {
            ranks[i] = parseRank(cards[i]);
            suits[i] = cards[i].charAt(cards[i].length() - 1);
            freq.put(ranks[i], freq.getOrDefault(ranks[i], 0) + 1);
        }

        boolean flush = suits[0] == suits[1] && suits[1] == suits[2]
                && suits[2] == suits[3] && suits[3] == suits[4];
        boolean straight = isStraight(ranks);

        if (flush && straight) return "Straight Flush";
        if (freq.containsValue(4)) return "Four of a Kind";
        if (freq.containsValue(3) && freq.containsValue(2)) return "Full House";
        if (flush) return "Flush";
        if (straight) return "Straight";
        if (freq.containsValue(3)) return "Three of a Kind";

        int pairs = 0;
        for (int count : freq.values()) {
            if (count == 2) pairs++;
        }
        if (pairs == 2) return "Two Pair";
        if (pairs == 1) return "Pair";
        return "High Card";
    }

    private static int parseRank(String card) {
        String rank = card.substring(0, card.length() - 1);
        return switch (rank) {
            case "A" -> 14;
            case "K" -> 13;
            case "Q" -> 12;
            case "J" -> 11;
            default -> Integer.parseInt(rank);
        };
    }

    private static boolean isStraight(int[] ranks) {
        int[] copy = Arrays.copyOf(ranks, ranks.length);
        Arrays.sort(copy);
        if (isConsecutive(copy)) {
            return true;
        }
        // A-2-3-4-5: trata Ás como 1
        for (int i = 0; i < copy.length; i++) {
            if (copy[i] == 14) {
                copy[i] = 1;
            }
        }
        Arrays.sort(copy);
        return isConsecutive(copy);
    }

    private static boolean isConsecutive(int[] sorted) {
        for (int i = 1; i < sorted.length; i++) {
            if (sorted[i] == sorted[i - 1]) {
                return false;
            }
            if (sorted[i] - sorted[i - 1] != 1) {
                return false;
            }
        }
        return true;
    }
}
