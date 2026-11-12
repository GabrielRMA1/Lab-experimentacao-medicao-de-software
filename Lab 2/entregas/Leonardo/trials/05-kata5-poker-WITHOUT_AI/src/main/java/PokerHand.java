import java.util.HashMap;
import java.util.Map;

public class PokerHand {
    public static String evaluate(String[] cards) {
        int[] ranks = new int[5];
        char[] suits = new char[5];
        for (int i = 0; i < cards.length; i++) {
            String card = cards[i];
            suits[i] = card.charAt(card.length() - 1);
            String r = card.substring(0, card.length() - 1);
            ranks[i] = rankValue(r);
        }

        Map<Integer, Integer> counts = new HashMap<Integer, Integer>();
        for (int i = 0; i < ranks.length; i++) {
            Integer current = counts.get(ranks[i]);
            if (current == null) {
                counts.put(ranks[i], 1);
            } else {
                counts.put(ranks[i], current + 1);
            }
        }

        boolean sameSuit = true;
        for (int i = 1; i < suits.length; i++) {
            if (suits[i] != suits[0]) {
                sameSuit = false;
            }
        }

        if (sameSuit) {
            return "Flush";
        }

        int howManyPairs = 0;
        for (Integer c : counts.values()) {
            if (c == 2) {
                howManyPairs = howManyPairs + 1;
            }
        }
        if (howManyPairs == 1) {
            return "Pair";
        }
        if (howManyPairs == 2) {
            return "Two Pair";
        }
        if (counts.containsValue(3) && counts.containsValue(2)) {
            return "Full House";
        }
        if (counts.containsValue(3)) {
            return "Three of a Kind";
        }
        if (counts.containsValue(4)) {
            return "Four of a Kind";
        }
        return "High Card";
    }

    private static int rankValue(String r) {
        if (r.equals("A")) return 14;
        if (r.equals("K")) return 13;
        if (r.equals("Q")) return 12;
        if (r.equals("J")) return 11;
        return Integer.parseInt(r);
    }
}
