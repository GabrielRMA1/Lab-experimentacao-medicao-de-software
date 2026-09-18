import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

public class PokerHand {
    public static String evaluate(String[] cards) {
        List<Card> parsed = parseCards(cards);
        if (isStraightFlush(parsed)) return "Straight Flush";
        if (maxFrequency(parsed) == 4) return "Four of a Kind";
        if (isFullHouse(parsed)) return "Full House";
        if (isFlush(parsed)) return "Flush";
        if (isStraight(parsed)) return "Straight";
        if (maxFrequency(parsed) == 3) return "Three of a Kind";
        int pairs = countPairs(parsed);
        if (pairs == 2) return "Two Pair";
        if (pairs == 1) return "Pair";
        return "High Card";
    }

    private static List<Card> parseCards(String[] cards) {
        List<Card> parsed = new ArrayList<>();
        for (String raw : cards) {
            parsed.add(Card.parse(raw));
        }
        return parsed;
    }

    private static boolean isFlush(List<Card> cards) {
        char suit = cards.get(0).suit;
        for (Card card : cards) {
            if (card.suit != suit) {
                return false;
            }
        }
        return true;
    }

    private static boolean isStraight(List<Card> cards) {
        List<Integer> ranks = new ArrayList<>();
        for (Card card : cards) {
            ranks.add(card.rank);
        }
        Collections.sort(ranks);
        if (consecutive(ranks)) {
            return true;
        }
        List<Integer> wheel = new ArrayList<>();
        for (Integer rank : ranks) {
            wheel.add(rank == 14 ? 1 : rank);
        }
        Collections.sort(wheel);
        return consecutive(wheel);
    }

    private static boolean consecutive(List<Integer> ranks) {
        Set<Integer> unique = new HashSet<>(ranks);
        if (unique.size() != 5) {
            return false;
        }
        return ranks.get(4) - ranks.get(0) == 4;
    }

    private static boolean isStraightFlush(List<Card> cards) {
        return isFlush(cards) && isStraight(cards);
    }

    private static boolean isFullHouse(List<Card> cards) {
        return maxFrequency(cards) == 3 && countPairs(cards) == 1;
    }

    private static int maxFrequency(List<Card> cards) {
        int max = 0;
        for (Card a : cards) {
            int count = 0;
            for (Card b : cards) {
                if (a.rank == b.rank) {
                    count++;
                }
            }
            if (count > max) {
                max = count;
            }
        }
        return max;
    }

    private static int countPairs(List<Card> cards) {
        Set<Integer> seen = new HashSet<>();
        int pairs = 0;
        for (Card a : cards) {
            if (seen.contains(a.rank)) {
                continue;
            }
            int count = 0;
            for (Card b : cards) {
                if (a.rank == b.rank) {
                    count++;
                }
            }
            if (count == 2) {
                pairs++;
            }
            seen.add(a.rank);
        }
        return pairs;
    }

    private static final class Card {
        private final int rank;
        private final char suit;

        private Card(int rank, char suit) {
            this.rank = rank;
            this.suit = suit;
        }

        private static Card parse(String raw) {
            char suit = raw.charAt(raw.length() - 1);
            String rankPart = raw.substring(0, raw.length() - 1);
            int rank = switch (rankPart) {
                case "A" -> 14;
                case "K" -> 13;
                case "Q" -> 12;
                case "J" -> 11;
                default -> Integer.parseInt(rankPart);
            };
            return new Card(rank, suit);
        }
    }
}
