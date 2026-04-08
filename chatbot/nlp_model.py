from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB

# Training data
training_sentences = [
    # Side effects
    "side effects of contraceptives",
    "what are the effects of birth control",
    "does implant have side effects",

    # Recommendation
    "recommend a contraceptive",
    "best birth control method",
    "which method should I use",

    # Facility
    "health facilities near me",
    "where is the nearest clinic",
    "find hospital",

    # Nearest
    "nearest health facility",
    "closest clinic to me",
    "recommend nearest facility",

    # Free
    "free health services",
    "which clinics are free",

    # Private
    "private hospitals",
    "private clinics near me"
]
training_sentences += [
    "which free facilities can i go to",
    "free clinics near me",
    "where can i get free health services",
    "nearby facilities for contraceptive information",
    "where can i get information about contraceptives",
    "recommend nearby clinics",
    "clinics near me for family planning",
]

training_labels = [
    "side_effect",
    "side_effect",
    "side_effect",

    "recommendation",
    "recommendation",
    "recommendation",

    "facility",
    "nearest_facility",
    "facility",

    "nearest_facility",
    "nearest_facility",
    "nearest_facility",

    "free_facility",
    "free_facility",

    "private_facility",
    "private_facility"
]
training_labels += [
    "free_facility",
    "free_facility",
    "free_facility",
    "nearest_facility",
    "facility",
    "nearest_facility",
    "facility",
]

# Vectorizer
vectorizer = TfidfVectorizer()

X = vectorizer.fit_transform(training_sentences)

# Model
model = MultinomialNB()
model.fit(X, training_labels)


def predict_intent(message):
    X_test = vectorizer.transform([message])
    return model.predict(X_test)[0]