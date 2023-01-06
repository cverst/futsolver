def team_rating(player_ratings):
    base_rating = sum(player_ratings)
    average_rating = base_rating / len(player_ratings)
    excess_rating = [
        rating - average_rating
        for rating in player_ratings
        if rating - average_rating > 0
    ]
    total_rating = base_rating + sum(excess_rating)
    rounded_rating = round(total_rating)
    final_rating = rounded_rating // len(player_ratings)
    return final_rating
