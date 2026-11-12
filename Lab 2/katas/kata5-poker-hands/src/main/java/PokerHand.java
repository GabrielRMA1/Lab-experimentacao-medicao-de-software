import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class PokerHand {
    public static String evaluate(String[] cards) {
        if (cards == null || cards.length != 5) {
            throw new IllegalArgumentException("Uma mão de pôquer deve conter exatamente 5 cartas");
        }

        List<Integer> ranks = new ArrayList<>();
        List<Character> suits = new ArrayList<>();
        Map<Integer, Integer> frequency = new HashMap<>();

        for (String card : cards) {
            if (card == null || card.length() < 2) {
                throw new IllegalArgumentException("Carta inválida: " + card);
            }

            String rankPart = card.substring(0, card.length() - 1);
            char suit = card.charAt(card.length() - 1);

            int rank = parseRank(rankPart);
            ranks.add(rank);
            suits.add(suit);
            frequency.put(rank, frequency.getOrDefault(rank, 0) + 1);
        }

        boolean flush = suits.stream().distinct().count() == 1;
        boolean straight = isStraight(ranks);

        if (flush && straight) {
            return "Straight Flush";
        }
        if (frequency.containsValue(4)) {
            return "Four of a Kind";
        }
        if (frequency.containsValue(3) && frequency.containsValue(2)) {
            return "Full House";
        }
        if (flush) {
            return "Flush";
        }
        if (straight) {
            return "Straight";
        }
        if (frequency.containsValue(3)) {
            return "Three of a Kind";
        }
        long pairCount = frequency.values().stream().filter(count -> count == 2).count();
        if (pairCount == 2) {
            return "Two Pair";
        }
        if (pairCount == 1) {
            return "Pair";
        }

        return "High Card";
    }

    private static int parseRank(String rankPart) {
        return switch (rankPart) {
            case "A" -> 14;
            case "K" -> 13;
            case "Q" -> 12;
            case "J" -> 11;
            default -> Integer.parseInt(rankPart);
        };
    }

    private static boolean isStraight(List<Integer> ranks) {
        List<Integer> values = new ArrayList<>(ranks);
        Collections.sort(values);

        if (values.contains(14)) {
            List<Integer> adjusted = new ArrayList<>(values);
            adjusted.remove(Integer.valueOf(14));
            adjusted.add(1);
            Collections.sort(adjusted);
            values = adjusted;
        }

        for (int i = 1; i < values.size(); i++) {
            if (values.get(i) - values.get(i - 1) != 1) {
                return false;
            }
        }

        return values.size() == 5;
    }
}