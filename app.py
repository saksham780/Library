import os
from flask import Flask, jsonify, request, render_template, abort
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import date, timedelta, datetime
from sqlalchemy import or_, func

from models import db, Book, Member, Transaction

# ── Book Chapters & Pages Data ────────────────────────────────────────────────
# Keyed by book title (exact match). Used by /api/books/<id>/chapters endpoint.
BOOK_CHAPTERS = {
    '1984': {
        'pages': 328,
        'chapters': [
            'Part One — Chapter I',   'Part One — Chapter II',   'Part One — Chapter III',
            'Part One — Chapter IV',  'Part One — Chapter V',    'Part One — Chapter VI',
            'Part One — Chapter VII', 'Part One — Chapter VIII',
            'Part Two — Chapter I',   'Part Two — Chapter II',   'Part Two — Chapter III',
            'Part Two — Chapter IV',  'Part Two — Chapter V',    'Part Two — Chapter VI',
            'Part Two — Chapter VII', 'Part Two — Chapter VIII', 'Part Two — Chapter IX',
            'Part Two — Chapter X',
            'Part Three — Chapter I', 'Part Three — Chapter II', 'Part Three — Chapter III',
            'Part Three — Chapter IV','Part Three — Chapter V',  'Part Three — Chapter VI',
            'Appendix: The Principles of Newspeak',
        ]
    },
    'Animal Farm': {
        'pages': 112,
        'chapters': [
            'Chapter 1 — Old Major\'s Dream',    'Chapter 2 — The Rebellion',
            'Chapter 3 — The Harvest',            'Chapter 4 — Battle of the Cowshed',
            'Chapter 5 — Snowball\'s Expulsion',  'Chapter 6 — Building the Windmill',
            'Chapter 7 — The Hens\' Revolt',      'Chapter 8 — Battle of the Windmill',
            'Chapter 9 — Boxer\'s Fate',           'Chapter 10 — The Pigs Walk Upright',
        ]
    },
    'Brave New World': {
        'pages': 311,
        'chapters': [
            'Chapter 1 — The Central London Hatchery',  'Chapter 2 — Conditioning',
            'Chapter 3 — Mustapha Mond',                'Chapter 4 — Bernard Marx',
            'Chapter 5 — Solidarity Service',            'Chapter 6 — The Reservation',
            'Chapter 7 — The Savage',                   'Chapter 8 — John\'s Childhood',
            'Chapter 9 — The Soma Holiday',             'Chapter 10 — The Director\'s Shame',
            'Chapter 11 — London',                      'Chapter 12 — The Lectures',
            'Chapter 13 — Lenina\'s Desire',            'Chapter 14 — The Hospital',
            'Chapter 15 — The Riot',                    'Chapter 16 — Mustapha Mond\'s Choice',
            'Chapter 17 — God and Soma',                'Chapter 18 — The Lighthouse',
        ]
    },
    'The Great Gatsby': {
        'pages': 180,
        'chapters': [
            'Chapter 1 — Nick Arrives on Long Island',  'Chapter 2 — The Valley of Ashes',
            'Chapter 3 — Gatsby\'s Party',               'Chapter 4 — Gatsby\'s Past',
            'Chapter 5 — The Green Light',               'Chapter 6 — Gatsby\'s True Origin',
            'Chapter 7 — The Confrontation',             'Chapter 8 — Myrtle\'s Death',
            'Chapter 9 — Aftermath',
        ]
    },
    'To Kill a Mockingbird': {
        'pages': 324,
        'chapters': [
            'Chapter 1 — Maycomb, Alabama',          'Chapter 2 — Scout\'s First Day',
            'Chapter 3 — Walter Cunningham',          'Chapter 4 — The Tire Game',
            'Chapter 5 — Miss Maudie',                'Chapter 6 — Boo\'s House at Night',
            'Chapter 7 — The Knothole',               'Chapter 8 — The Snowman',
            'Chapter 9 — Christmas with Atticus',     'Chapter 10 — The Mad Dog',
            'Chapter 11 — Mrs Dubose',                'Chapter 12 — Calpurnia\'s Church',
            'Chapter 13 — Aunt Alexandra Arrives',    'Chapter 14 — Dill Runs Away',
            'Chapter 15 — The Jail',                  'Chapter 16 — The Trial Begins',
            'Chapter 17 — Bob Ewell\'s Testimony',    'Chapter 18 — Mayella\'s Testimony',
            'Chapter 19 — Tom Robinson Testifies',    'Chapter 20 — Atticus Speaks',
            'Chapter 21 — The Verdict',               'Chapter 22 — Aftermath',
            'Chapter 23 — Atticus on Justice',        'Chapter 24 — The Missionary Tea',
            'Chapter 25 — Tom\'s Death',              'Chapter 26 — School',
            'Chapter 27 — Halloween Pageant',         'Chapter 28 — The Attack',
            'Chapter 29 — Boo\'s Appearance',         'Chapter 30 — Heck Tate\'s Decision',
            'Chapter 31 — Boo\'s Porch',
        ]
    },
    'Pride and Prejudice': {
        'pages': 432,
        'chapters': [
            'Volume I — Chapter 1',   'Volume I — Chapter 2',   'Volume I — Chapter 3',
            'Volume I — Chapter 4',   'Volume I — Chapter 5',   'Volume I — Chapter 6',
            'Volume I — Chapter 7',   'Volume I — Chapter 8',   'Volume I — Chapter 9',
            'Volume I — Chapter 10',  'Volume I — Chapter 11',  'Volume I — Chapter 12',
            'Volume I — Chapter 13',  'Volume I — Chapter 14',  'Volume I — Chapter 15',
            'Volume I — Chapter 16',  'Volume I — Chapter 17',  'Volume I — Chapter 18',
            'Volume I — Chapter 19',  'Volume I — Chapter 20',  'Volume I — Chapter 21',
            'Volume I — Chapter 22',  'Volume I — Chapter 23',
            'Volume II — Chapter 1',  'Volume II — Chapter 2',  'Volume II — Chapter 3',
            'Volume II — Chapter 4',  'Volume II — Chapter 5',  'Volume II — Chapter 6',
            'Volume II — Chapter 7',  'Volume II — Chapter 8',  'Volume II — Chapter 9',
            'Volume II — Chapter 10', 'Volume II — Chapter 11', 'Volume II — Chapter 12',
            'Volume II — Chapter 13', 'Volume II — Chapter 14', 'Volume II — Chapter 15',
            'Volume II — Chapter 16', 'Volume II — Chapter 17', 'Volume II — Chapter 18',
            'Volume II — Chapter 19',
            'Volume III — Chapter 1', 'Volume III — Chapter 2', 'Volume III — Chapter 3',
            'Volume III — Chapter 4', 'Volume III — Chapter 5', 'Volume III — Chapter 6',
            'Volume III — Chapter 7', 'Volume III — Chapter 8', 'Volume III — Chapter 9',
            'Volume III — Chapter 10','Volume III — Chapter 11','Volume III — Chapter 12',
            'Volume III — Chapter 13','Volume III — Chapter 14','Volume III — Chapter 15',
            'Volume III — Chapter 16','Volume III — Chapter 17','Volume III — Chapter 18',
            'Volume III — Chapter 19',
        ]
    },
    'Harry Potter and the Philosopher\'s Stone': {
        'pages': 332,
        'chapters': [
            '1. The Boy Who Lived',           '2. The Vanishing Glass',
            '3. The Letters from No One',      '4. The Keeper of the Keys',
            '5. Diagon Alley',                 '6. The Journey from Platform Nine and Three-Quarters',
            '7. The Sorting Hat',              '8. The Potions Master',
            '9. The Midnight Duel',            '10. Hallowe\'en',
            '11. Quidditch',                   '12. The Mirror of Erised',
            '13. Nicolas Flamel',              '14. Norbert the Norwegian Ridgeback',
            '15. The Forbidden Forest',        '16. Through the Trapdoor',
            '17. The Man with Two Faces',
        ]
    },
    'The Alchemist': {
        'pages': 208,
        'chapters': [
            'Prologue',
            'Part One — The Boy and His Dream',   'Part One — The Old King',
            'Part One — The Journey Begins',       'Part One — The Crystal Merchant',
            'Part Two — The Caravan',              'Part Two — The Oasis',
            'Part Two — The Alchemist',            'Part Two — The Soul of the World',
            'Part Two — The Pyramids',             'Epilogue',
        ]
    },
    'Atomic Habits': {
        'pages': 320,
        'chapters': [
            'Introduction: My Story',
            '1. The Surprising Power of Atomic Habits',
            '2. How Your Habits Shape Your Identity (and Vice Versa)',
            '3. How to Build Better Habits in 4 Simple Steps',
            '4. The Man Who Didn\'t Look Right',
            '5. The Best Way to Start a New Habit',
            '6. Motivation Is Overrated; Environment Often Matters More',
            '7. The Secret to Self-Control',
            '8. How to Make a Habit Irresistible',
            '9. The Role of Family and Friends in Shaping Your Habits',
            '10. How to Find and Fix the Causes of Your Bad Habits',
            '11. Walk Slowly, but Never Backward',
            '12. The Law of Least Effort',
            '13. How to Stop Procrastinating by Using the Two-Minute Rule',
            '14. How to Make Good Habits Inevitable and Bad Habits Impossible',
            '15. The Cardinal Rule of Behavior Change',
            '16. How to Stick with Good Habits Every Day',
            '17. How an Accountability Partner Can Change Everything',
            '18. The Truth About Talent (When Genes Matter and When They Don\'t)',
            '19. The Goldilocks Rule: How to Stay Motivated',
            '20. The Downside of Creating Good Habits',
            'Conclusion: The Secret to Results That Last',
            'Appendix: Little Lessons from the Four Laws',
        ]
    },
    'The Psychology of Money': {
        'pages': 256,
        'chapters': [
            'Introduction: The Greatest Show on Earth',
            '1. No One\'s Crazy',
            '2. Luck & Risk',
            '3. Never Enough',
            '4. Confounding Compounding',
            '5. Getting Wealthy vs. Staying Wealthy',
            '6. Tails, You Win',
            '7. Freedom',
            '8. Man in the Car Paradox',
            '9. Wealth is What You Don\'t See',
            '10. Save Money',
            '11. Reasonable > Rational',
            '12. Surprise!',
            '13. Room for Error',
            '14. You\'ll Change',
            '15. Nothing\'s Free',
            '16. You & Me',
            '17. The Seduction of Pessimism',
            '18. When You\'ll Believe Anything',
            '19. All Together Now',
            '20. Confessions',
            'Postscript: A Brief History of Why the U.S. Consumer Thinks the Way They Do',
        ]
    },
    'Sapiens: A Brief History of Humankind': {
        'pages': 443,
        'chapters': [
            'Introduction: An Animal of No Significance',
            'Part One: The Cognitive Revolution',
            '1. History\'s Biggest Fraud',
            '2. History\'s Most Successful Religion',
            '3. Money — The Story of the Greatest Con Artist',
            '4. Imperial Visions',
            'Part Two: The Agricultural Revolution',
            '5. A Permanent Revolution',
            '6. Building Pyramids',
            '7. Memory Overload',
            '8. There is No Justice in History',
            'Part Three: The Unification of Humankind',
            '9. The Arrow of History',
            '10. The Scent of Money',
            '11. Imperial Visions',
            '12. The Law of Religion',
            '13. The Secret of Success',
            'Part Four: The Scientific Revolution',
            '14. The Discovery of Ignorance',
            '15. The Marriage of Science and Empire',
            '16. The Capitalist Creed',
            '17. The Wheels of Industry',
            '18. A Permanent Revolution',
            '19. And They Lived Happily Ever After',
            '20. The End of Homo Sapiens',
            'Afterword: The Animal That Became a God',
        ]
    },
    'Thinking, Fast and Slow': {
        'pages': 499,
        'chapters': [
            'Introduction',
            'Part One: Two Systems',
            '1. The Characters of the Story',     '2. Attention and Effort',
            '3. The Lazy Controller',              '4. The Associative Machine',
            '5. Cognitive Ease',                   '6. Norms, Surprises, and Causes',
            '7. A Machine for Jumping to Conclusions', '8. How Judgments Happen',
            '9. Answering an Easier Question',
            'Part Two: Heuristics and Biases',
            '10. The Law of Small Numbers',        '11. Anchors',
            '12. The Science of Availability',     '13. Availability, Emotion, and Risk',
            '14. Tom W\'s Specialty',              '15. Linda: Less is More',
            '16. Causes Trump Statistics',         '17. Regression to the Mean',
            '18. Taming Intuitive Predictions',
            'Part Three: Overconfidence',
            '19. The Illusion of Understanding',   '20. The Illusion of Validity',
            '21. Intuitions vs. Formulas',         '22. Expert Intuition: When Can We Trust It?',
            '23. The Outside View',                '24. The Engine of Capitalism',
            'Part Four: Choices',
            '25. Bernoulli\'s Errors',             '26. Prospect Theory',
            '27. The Endowment Effect',            '28. Bad Events',
            '29. The Fourfold Pattern',            '30. Rare Events',
            '31. Risk Policies',                   '32. Keeping Score',
            '33. Reversals',                       '34. Frames and Reality',
            'Part Five: Two Selves',
            '35. Two Selves',                      '36. Life as a Story',
            '37. Experienced Well-Being',          '38. Thinking About Life',
            'Conclusions',
        ]
    },
    'The Hitchhiker\'s Guide to the Galaxy': {
        'pages': 193,
        'chapters': [
            'Chapter 1 — A Thursday Afternoon',         'Chapter 2 — Arthur and Ford',
            'Chapter 3 — The Vogon Constructor Fleet',  'Chapter 4 — Poetry',
            'Chapter 5 — Zaphod Beeblebrox',            'Chapter 6 — Heart of Gold',
            'Chapter 7 — Magrathea',                    'Chapter 8 — The Answer',
            'Chapter 9 — Slartibartfast',               'Chapter 10 — The Earth\'s Purpose',
            'Chapter 11 — The Restaurant',              'Chapter 12 — Milliways',
            'Chapter 13 — The Great Question',          'Chapter 14 — The End of the Universe',
            'Chapter 15 — Earth Mark II',               'Chapter 16 — The Mice',
            'Chapter 17 — Don\'t Panic',                'Chapter 18 — 42',
            'Chapter 19 — So Long…',                   'Chapter 20 — And Thanks for All the Fish',
            'Chapter 21 — The New Planet',              'Chapter 22 — Epilogue',
        ]
    },
    'Dune': {
        'pages': 896,
        'chapters': [
            'Prologue',
            'Book One: Dune',
            '— Chapter 1: The Atreides Heir',       '— Chapter 2: The Bene Gesserit',
            '— Chapter 3: The Spice Must Flow',     '— Chapter 4: Arrival on Arrakis',
            '— Chapter 5: The Sietch',              '— Chapter 6: The Sardaukar',
            '— Chapter 7: Betrayal',                '— Chapter 8: Into the Desert',
            '— Chapter 9: The Fremen',              '— Chapter 10: Stilgar',
            '— Chapter 11: Learning the Ways',      '— Chapter 12: The Water of Life',
            '— Chapter 13: The Worm Rider',         '— Chapter 14: Lady Jessica',
            'Book Two: Muad\'Dib',
            '— Chapter 15: The Prophet',            '— Chapter 16: The War',
            '— Chapter 17: Chani',                  '— Chapter 18: The Voice',
            '— Chapter 19: The Jihad',              '— Chapter 20: The Golden Path',
            'Book Three: The Prophet',
            '— Chapter 21: Victory',                '— Chapter 22: The Throne',
            '— Chapter 23: The God Emperor',        'Appendix',
        ]
    },
    'The Hobbit': {
        'pages': 310,
        'chapters': [
            '1. An Unexpected Party',               '2. Roast Mutton',
            '3. A Short Rest',                      '4. Over Hill and Under Hill',
            '5. Riddles in the Dark',               '6. Out of the Frying-Pan into the Fire',
            '7. Queer Lodgings',                    '8. Flies and Spiders',
            '9. Barrels Out of Bond',               '10. A Warm Welcome',
            '11. On the Doorstep',                  '12. Inside Information',
            '13. Not at Home',                      '14. Fire and Water',
            '15. The Gathering of the Clouds',      '16. A Thief in the Night',
            '17. The Clouds Burst',                 '18. The Return Journey',
            '19. The Last Stage',
        ]
    },
    'The Lord of the Rings': {
        'pages': 1216,
        'chapters': [
            'Prologue: Concerning Hobbits',
            'The Fellowship of the Ring — Part One',
            '1. A Long-expected Party',             '2. The Shadow of the Past',
            '3. Three is Company',                  '4. A Short Cut to Mushrooms',
            '5. A Conspiracy Unmasked',             '6. The Old Forest',
            '7. In the House of Tom Bombadil',      '8. Fog on the Barrow-Downs',
            '9. At the Sign of The Prancing Pony',  '10. Strider',
            '11. A Knife in the Dark',              '12. Flight to the Ford',
            'The Fellowship of the Ring — Part Two',
            '13. Many Meetings',                    '14. The Council of Elrond',
            '15. The Ring Goes South',              '16. A Journey in the Dark',
            '17. The Bridge of Khazad-dûm',         '18. Lothlórien',
            '19. The Mirror of Galadriel',          '20. Farewell to Lórien',
            '21. The Great River',                  '22. The Breaking of the Fellowship',
            'The Two Towers',
            '23. The Departure of Boromir',         '24. The Riders of Rohan',
            '25. The Uruk-hai',                     '26. Treebeard',
            '27. The White Rider',                  '28. Helm\'s Deep',
            '29. The Road to Isengard',             '30. Flotsam and Jetsam',
            '31. The Voice of Saruman',             '32. The Palantír',
            '33. The Taming of Sméagol',            '34. The Stairs of Cirith Ungol',
            '35. Shelob\'s Lair',                   '36. The Choices of Master Samwise',
            'The Return of the King',
            '37. Minas Tirith',                     '38. The Siege of Gondor',
            '39. The Battle of the Pelennor Fields','40. The Houses of Healing',
            '41. The Black Gate Opens',             '42. The Tower of Cirith Ungol',
            '43. Mount Doom',                       '44. The Field of Cormallen',
            '45. The Steward and the King',         '46. The Grey Havens',
            'Appendices',
        ]
    },
    'The Name of the Wind': {
        'pages': 662,
        'chapters': [
            'Prologue: A Silence of Three Parts',
            'Chapter 1 — A Place for Demons',        'Chapter 2 — A Beautiful Day',
            'Chapter 3 — Wood and Word',             'Chapter 4 — Tar and Tin',
            'Chapter 5 — A Rare Vintage',            'Chapter 6 — The Price of a Loaf of Bread',
            'Chapter 7 — Of Bastards, Barmaids, and Bridges', 'Chapter 8 — Thieves, Heretics, and Whores',
            'Chapter 9 — Promises Made by Firelight','Chapter 10 — Arliden\'s Brilliant Plan',
            'Chapter 11 — The Ignorant Edema Ruh',   'Chapter 12 — Interlude — The Listener',
            'Chapter 13 — Skarpi\'s First Story',    'Chapter 14 — Skarpi\'s Second Story',
            'Chapter 15 — Distractions and Farewells','Chapter 16 — Hope',
            'Chapter 17 — Interlude — A Bit of Fiddle','Chapter 18 — Roads to Safe Places',
            'Chapter 19 — Fingers and Strings',      'Chapter 20 — Bloody Hands and Gentle Words',
            'Chapter 21 — Admissions',               'Chapter 22 — A Beautiful Game',
            'Chapter 23 — The University',           'Chapter 24 — Admissions',
            'Chapter 25 — Wrongful Appointment of Irresponsible Parties',
            'Epilogue — The Waystone Inn',
        ]
    },
    'Crime and Punishment': {
        'pages': 545,
        'chapters': [
            'Part I — Chapter 1',  'Part I — Chapter 2',  'Part I — Chapter 3',
            'Part I — Chapter 4',  'Part I — Chapter 5',  'Part I — Chapter 6',  'Part I — Chapter 7',
            'Part II — Chapter 1', 'Part II — Chapter 2', 'Part II — Chapter 3',
            'Part II — Chapter 4', 'Part II — Chapter 5', 'Part II — Chapter 6', 'Part II — Chapter 7',
            'Part III — Chapter 1','Part III — Chapter 2','Part III — Chapter 3',
            'Part III — Chapter 4','Part III — Chapter 5','Part III — Chapter 6',
            'Part IV — Chapter 1', 'Part IV — Chapter 2', 'Part IV — Chapter 3',
            'Part IV — Chapter 4', 'Part IV — Chapter 5', 'Part IV — Chapter 6',
            'Part V — Chapter 1',  'Part V — Chapter 2',  'Part V — Chapter 3',
            'Part V — Chapter 4',  'Part V — Chapter 5',
            'Part VI — Chapter 1', 'Part VI — Chapter 2', 'Part VI — Chapter 3',
            'Part VI — Chapter 4', 'Part VI — Chapter 5', 'Part VI — Chapter 6', 'Part VI — Chapter 7', 'Part VI — Chapter 8',
            'Epilogue — Chapter 1','Epilogue — Chapter 2',
        ]
    },
    'The Little Prince': {
        'pages': 96,
        'chapters': [
            'Chapter 1 — The Boa Constrictor',        'Chapter 2 — The Prince Appears',
            'Chapter 3 — Learning About the Prince',  'Chapter 4 — The Little Planet',
            'Chapter 5 — The Baobabs',                'Chapter 6 — The Sunsets',
            'Chapter 7 — The Flower\'s Thorns',       'Chapter 8 — The Rose',
            'Chapter 9 — The Departure',              'Chapter 10 — The King\'s Asteroid',
            'Chapter 11 — The Conceited Man',         'Chapter 12 — The Tippler',
            'Chapter 13 — The Businessman',           'Chapter 14 — The Lamplighter',
            'Chapter 15 — The Geographer',            'Chapter 16 — The Seventh Planet',
            'Chapter 17 — The Serpent',               'Chapter 18 — The Flower in the Desert',
            'Chapter 19 — The Mountain',              'Chapter 20 — The Rose Garden',
            'Chapter 21 — The Fox',                   'Chapter 22 — The Switchman',
            'Chapter 23 — The Merchant',              'Chapter 24 — The Well',
            'Chapter 25 — The Secret',                'Chapter 26 — One More Sunset',
            'Chapter 27 — The Aftermath',
        ]
    },
    'Rich Dad Poor Dad': {
        'pages': 336,
        'chapters': [
            'Introduction: Rich Dad, Poor Dad',
            'Chapter 1 — Rich Dad, Poor Dad',
            'Chapter 2 — The Rich Don\'t Work for Money',
            'Chapter 3 — Why Teach Financial Literacy?',
            'Chapter 4 — Mind Your Own Business',
            'Chapter 5 — The History of Taxes and the Power of Corporations',
            'Chapter 6 — The Rich Invent Money',
            'Chapter 7 — Work to Learn — Don\'t Work for Money',
            'Chapter 8 — Overcoming Obstacles',
            'Chapter 9 — Getting Started',
            'Chapter 10 — Still Want More? Here Are Some To Do\'s',
            'Epilogue',
        ]
    },
    'Man\'s Search for Meaning': {
        'pages': 165,
        'chapters': [
            'Preface',
            'Part One: Experiences in a Concentration Camp',
            '— The Existential Vacuum',             '— Finding Meaning in Suffering',
            '— Logotherapeutic Techniques',         '— The Meaning of Suffering',
            'Part Two: Logotherapy in a Nutshell',
            '— Freedom of Will',                    '— Will to Meaning',
            '— Meaning of Life',                    '— The Existential Vacuum',
            '— The Meaning of Life',                '— The Meaning of Love',
            '— The Meaning of Suffering',           '— The Super-Meaning',
            '— Life\'s Transitoriness',             '— Logotherapy as a Technique',
            'Postscript 1984: The Case for a Tragic Optimism',
        ]
    },
    'Deep Work': {
        'pages': 304,
        'chapters': [
            'Introduction',
            'Part One: The Idea',
            'Chapter 1 — Deep Work is Valuable',
            'Chapter 2 — Deep Work is Rare',
            'Chapter 3 — Deep Work is Meaningful',
            'Part Two: The Rules',
            'Rule 1 — Work Deeply',
            'Rule 2 — Embrace Boredom',
            'Rule 3 — Quit Social Media',
            'Rule 4 — Drain the Shallows',
            'Conclusion',
        ]
    },
    'Meditations': {
        'pages': 254,
        'chapters': [
            'Book I — Debts and Lessons',        'Book II — On the River Gran, Among the Quadi',
            'Book III — In Carnuntum',           'Book IV',
            'Book V',                            'Book VI',
            'Book VII',                          'Book VIII',
            'Book IX',                           'Book X',
            'Book XI',                           'Book XII',
        ]
    },
    'The Subtle Art of Not Giving a F*ck': {
        'pages': 224,
        'chapters': [
            'Chapter 1 — Don\'t Try',
            'Chapter 2 — Happiness is a Problem',
            'Chapter 3 — You Are Not Special',
            'Chapter 4 — The Value of Suffering',
            'Chapter 5 — You Are Always Choosing',
            'Chapter 6 — You\'re Wrong About Everything (But So Am I)',
            'Chapter 7 — Failure is the Way Forward',
            'Chapter 8 — The Importance of Saying No',
            'Chapter 9 — …And Then You Die',
            'Conclusion: The Subtle Art of Not Giving a F*ck',
        ]
    },
    'Ikigai: The Japanese Secret to a Long and Happy Life': {
        'pages': 208,
        'chapters': [
            'Prologue',
            'Chapter 1 — Ikigai: The Art of Staying Young',
            'Chapter 2 — Antiaging Secrets',
            'Chapter 3 — From Logotherapy to Ikigai',
            'Chapter 4 — Find Flow in Everything You Do',
            'Chapter 5 — Masters of Longevity',
            'Chapter 6 — Lessons from Japan\'s Centenarians',
            'Chapter 7 — The Ikigai Diet',
            'Chapter 8 — Gentle Movements, Long Life',
            'Chapter 9 — Resilience and Wabi-sabi',
            'Epilogue',
        ]
    },
    'Educated': {
        'pages': 334,
        'chapters': [
            'Part One: Junk',
            'Chapter 1 — Choose the Good',       'Chapter 2 — Worm Farmer',
            'Chapter 3 — Cream Rises',            'Chapter 4 — Apache Women',
            'Chapter 5 — Honest Dirt',            'Chapter 6 — Shield and Buckler',
            'Chapter 7 — The Lord Will Provide',  'Chapter 8 — Tiny Powder Kegs',
            'Chapter 9 — Perfect in His Generations', 'Chapter 10 — Shield and Buckler Reprise',
            'Part Two: The Provost\'s Dilemma',
            'Chapter 11 — Instinct',              'Chapter 12 — Fish Eyes',
            'Chapter 13 — Silence in the Churches','Chapter 14 — My Feet No Longer Touch Earth',
            'Chapter 15 — No Longer Myself',      'Chapter 16 — Blood and Feathers',
            'Part Three: Educated',
            'Chapter 17 — To Keep It Holy',       'Chapter 18 — Blood and Bone',
            'Chapter 19 — In Her Bones She is the Earth', 'Chapter 20 — Reckonings',
            'Chapter 21 — Skullduggery',          'Chapter 22 — Whatever the Cost',
            'Epilogue',
        ]
    },
    'Becoming': {
        'pages': 448,
        'chapters': [
            'Prologue',
            'Part One: Becoming Me',
            '1. Euclid Avenue',   '2. Shields Avenue',  '3. Robbie',
            '4. Dandy',           '5. Whitney M. Young Magnet High School',
            'Part Two: Becoming Us',
            '6. Sidley & Austin', '7. Craig\'s Friend', '8. Seasons',
            '9. Multiplying',     '10. What We Carry',   '11. South Side Girl',
            'Part Three: Becoming More',
            '12. Showtime',       '13. Going High',      '14. The Campaigner',
            '15. A Girl You\'d Like', '16. Family Navigation', '17. Soldiering',
            '18. The Good Stuff', '19. Dancing',         '20. Morning Routines',
            'Epilogue',
        ]
    },
}

# ── Genre page-count ranges (min, max) for books not in BOOK_CHAPTERS ────────
GENRE_PAGES = {
    'Fiction':    (280, 420), 'Classics':   (200, 560), 'Fantasy':   (380, 720),
    'Sci-Fi':     (260, 520), 'Mystery':    (280, 380), 'Thriller':  (320, 480),
    'Horror':     (300, 440), 'Romance':    (260, 380), 'Dystopian': (260, 380),
    'Biography':  (300, 520), 'Self-Help':  (220, 340), 'Business':  (200, 320),
    'Psychology': (240, 400), 'Science':    (280, 480), 'History':   (300, 560),
    'Philosophy': (180, 340), 'Poetry':     (96,  210), 'Children':  (80,  260),
    'Travel':     (240, 360), 'Cooking':    (240, 380), 'Art':       (180, 320),
    'Religion':   (200, 400), 'Comics':     (160, 380),
}

GENRE_CHAPTER_TEMPLATES = {
    'Fiction':    ['Prologue', 'Part I — Beginnings', 'Part I — Chapter 2', 'Part I — Chapter 3',
                   'Part I — Chapter 4', 'Part II — Rising Action', 'Part II — Chapter 2',
                   'Part II — Chapter 3', 'Part III — The Turning Point', 'Part III — Chapter 2',
                   'Part III — Chapter 3', 'Part IV — Resolution', 'Epilogue'],
    'Classics':   ['Volume I — Chapter 1', 'Volume I — Chapter 2', 'Volume I — Chapter 3',
                   'Volume I — Chapter 4', 'Volume I — Chapter 5', 'Volume II — Chapter 1',
                   'Volume II — Chapter 2', 'Volume II — Chapter 3', 'Volume II — Chapter 4',
                   'Volume III — Chapter 1', 'Volume III — Chapter 2', 'Volume III — Chapter 3'],
    'Fantasy':    ['Prologue', 'Chapter 1 — A World Apart', 'Chapter 2 — The Call',
                   'Chapter 3 — Into the Unknown', 'Chapter 4 — The Quest',
                   'Chapter 5 — Allies and Enemies', 'Chapter 6 — The Dark Fortress',
                   'Chapter 7 — The Trial', 'Chapter 8 — The Revelation',
                   'Chapter 9 — The Final Battle', 'Epilogue'],
    'Sci-Fi':     ['Prologue', 'Part One — First Contact', 'Chapter 1 — Anomaly',
                   'Chapter 2 — The Signal', 'Chapter 3 — The Mission',
                   'Chapter 4 — Deep Space', 'Chapter 5 — First Contact',
                   'Part Two — Consequences', 'Chapter 6 — The Choice',
                   'Chapter 7 — Cascade', 'Chapter 8 — The Final Frontier',
                   'Epilogue — The New World'],
    'Mystery':    ['Chapter 1 — The Scene', 'Chapter 2 — The Victim',
                   'Chapter 3 — First Clues', 'Chapter 4 — Red Herrings',
                   'Chapter 5 — The Suspects', 'Chapter 6 — The Investigation',
                   'Chapter 7 — A Breakthrough', 'Chapter 8 — The Twist',
                   'Chapter 9 — Unmasked', 'Chapter 10 — Resolution'],
    'Thriller':   ['Chapter 1 — The Setup', 'Chapter 2 — The Threat',
                   'Chapter 3 — No Way Out', 'Chapter 4 — The Chase',
                   'Chapter 5 — False Leads', 'Chapter 6 — The Revelation',
                   'Chapter 7 — Double Cross', 'Chapter 8 — The Countdown',
                   'Chapter 9 — The Confrontation', 'Epilogue'],
    'Self-Help':  ['Introduction', 'Chapter 1 — The Foundation',
                   'Chapter 2 — The Mindset Shift', 'Chapter 3 — Core Principles',
                   'Chapter 4 — Building the Habit', 'Chapter 5 — Overcoming Obstacles',
                   'Chapter 6 — The Practice', 'Chapter 7 — Mastery',
                   'Chapter 8 — Living the Principles', 'Conclusion', 'Afterword'],
    'Biography':  ['Preface', 'Chapter 1 — Early Life', 'Chapter 2 — The Formative Years',
                   'Chapter 3 — First Steps', 'Chapter 4 — The Rise',
                   'Chapter 5 — Trials and Tribulations', 'Chapter 6 — The Turning Point',
                   'Chapter 7 — At the Peak', 'Chapter 8 — Legacy',
                   'Epilogue', 'Acknowledgements'],
    'Business':   ['Introduction', 'Chapter 1 — The Problem', 'Chapter 2 — The Opportunity',
                   'Chapter 3 — The Framework', 'Chapter 4 — Strategy',
                   'Chapter 5 — Execution', 'Chapter 6 — Scaling',
                   'Chapter 7 — Culture', 'Chapter 8 — The Future',
                   'Conclusion', 'Further Reading'],
    'History':    ['Preface', 'Chapter 1 — The World Before',
                   'Chapter 2 — The Catalyst', 'Chapter 3 — Key Players',
                   'Chapter 4 — The Conflict', 'Chapter 5 — Turning Points',
                   'Chapter 6 — Consequences', 'Chapter 7 — Aftermath',
                   'Chapter 8 — Legacy', 'Epilogue', 'Notes & Bibliography'],
    'Psychology': ['Foreword', 'Introduction', 'Chapter 1 — The Human Mind',
                   'Chapter 2 — The Unconscious', 'Chapter 3 — Behavior',
                   'Chapter 4 — Emotion', 'Chapter 5 — Cognition',
                   'Chapter 6 — Social Influence', 'Chapter 7 — Personality',
                   'Chapter 8 — Disorders', 'Chapter 9 — Healing',
                   'Conclusion', 'References'],
    'Romance':    ['Chapter 1 — First Meeting', 'Chapter 2 — The Connection',
                   'Chapter 3 — Growing Closer', 'Chapter 4 — Complications',
                   'Chapter 5 — Misunderstandings', 'Chapter 6 — The Break',
                   'Chapter 7 — Reconciliation', 'Chapter 8 — Love Declared',
                   'Epilogue'],
    'Horror':     ['Prologue — Something Wrong', 'Chapter 1 — Arrival',
                   'Chapter 2 — First Signs', 'Chapter 3 — The Presence',
                   'Chapter 4 — No Escape', 'Chapter 5 — The Truth',
                   'Chapter 6 — Into the Dark', 'Chapter 7 — The Horror Revealed',
                   'Chapter 8 — Final Stand', 'Epilogue'],
    'Poetry':     ['Part I', 'Part II', 'Part III', 'Part IV'],
    'Children':   ['Chapter 1', 'Chapter 2', 'Chapter 3', 'Chapter 4', 'Chapter 5',
                   'Chapter 6', 'Chapter 7', 'Chapter 8', 'Chapter 9', 'Chapter 10'],
    'Philosophy': ['Preface', 'Chapter 1 — The Question', 'Chapter 2 — The Argument',
                   'Chapter 3 — Counter-Arguments', 'Chapter 4 — A New Perspective',
                   'Chapter 5 — The Synthesis', 'Conclusion'],
    'Travel':     ['Prologue', 'Chapter 1 — Departure', 'Chapter 2 — First Impressions',
                   'Chapter 3 — Into the Unknown', 'Chapter 4 — The People',
                   'Chapter 5 — Lost and Found', 'Chapter 6 — Discoveries',
                   'Chapter 7 — The Return', 'Epilogue'],
    'Science':    ['Preface', 'Chapter 1 — The Question', 'Chapter 2 — The Discovery',
                   'Chapter 3 — The Evidence', 'Chapter 4 — The Theory',
                   'Chapter 5 — The Experiments', 'Chapter 6 — The Implications',
                   'Chapter 7 — The Future', 'Conclusion', 'Glossary'],
    'Cooking':    ['Introduction', 'Chapter 1 — The Essentials', 'Chapter 2 — Foundations',
                   'Chapter 3 — Breakfast & Brunch', 'Chapter 4 — Soups & Salads',
                   'Chapter 5 — Mains', 'Chapter 6 — Sides', 'Chapter 7 — Desserts',
                   'Chapter 8 — Special Occasions', 'Index'],
    'Art':        ['Introduction', 'Chapter 1 — The Beginning', 'Chapter 2 — The Renaissance',
                   'Chapter 3 — Baroque & Rococo', 'Chapter 4 — Romanticism',
                   'Chapter 5 — Modernism', 'Chapter 6 — Contemporary Art',
                   'Conclusion', 'Index of Artists'],
    'Religion':   ['Introduction', 'Chapter 1 — Origins', 'Chapter 2 — Core Beliefs',
                   'Chapter 3 — Practices', 'Chapter 4 — Sacred Texts',
                   'Chapter 5 — Key Figures', 'Chapter 6 — Influence',
                   'Chapter 7 — Modern Faith', 'Epilogue'],
    'Comics':     ['Part 1', 'Part 2', 'Part 3', 'Part 4', 'Part 5', 'Part 6'],
    'Dystopian':  ['Part One — The World', 'Chapter 1', 'Chapter 2', 'Chapter 3',
                   'Part Two — The Resistance', 'Chapter 4', 'Chapter 5', 'Chapter 6',
                   'Part Three — The Reckoning', 'Chapter 7', 'Chapter 8', 'Epilogue'],
}

def get_book_chapters(book):
    """Return dict with pages and chapters list for a book."""
    data = BOOK_CHAPTERS.get(book.title)
    if data:
        return data

    # Fall back to genre-based data
    genre = book.genre or 'Fiction'
    template = GENRE_CHAPTER_TEMPLATES.get(genre, GENRE_CHAPTER_TEMPLATES['Fiction'])
    page_range = GENRE_PAGES.get(genre, (280, 420))

    # Deterministic "random" page count from title hash
    import hashlib
    h = int(hashlib.md5(book.title.encode()).hexdigest(), 16)
    pages = page_range[0] + (h % (page_range[1] - page_range[0]))

    return {'pages': pages, 'chapters': template}


def create_app():
    app = Flask(__name__)
    CORS(app)

    # ── Database config ──────────────────────────────────────────────
    base_dir = os.path.abspath(os.path.dirname(__file__))
    db_url = os.environ.get(
        'DATABASE_URL',
        f"sqlite:///{os.path.join(base_dir, 'library.db')}"
    )
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)

    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-in-prod')

    db.init_app(app)

    with app.app_context():
        db.create_all()
        seed_demo_data()

    # ── Groq chatbot (lazy init so missing key doesn't crash startup) ──
    _groq_client = None

    def get_groq_client():
        nonlocal _groq_client
        if _groq_client is None:
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                return None
            try:
                from groq import Groq
                _groq_client = Groq(api_key=api_key)
            except Exception as e:
                print("Groq init error:", e)
                return None
        return _groq_client

    def ask_groq_for_books(user_message, books):
        client = get_groq_client()
        if client is None:
            return "⚠️ Chatbot is not configured. Please set the GROQ_API_KEY environment variable in your Render dashboard."
        try:
            book_info = ""
            for b in books:
                bestseller = " [BESTSELLER]" if b.get('is_bestseller') else ""
                rating = f" | Rating: {b['rating']}/5" if b.get('rating') else ""
                editions = f" | Editions: {b['editions']}" if b.get('editions') else ""
                book_info += f"- {b['title']} by {b['author']} ({b['year']}){bestseller}{rating}{editions}\n"

            prompt = f"""You are a friendly and knowledgeable library assistant.

The user is interacting with a library management system.
Only recommend books from the available books list below.
Give a short 2-line review for each recommended book.
Mention if a book is a bestseller or its rating when relevant.

User Question:
{user_message}

Available Books:
{book_info}

Give a friendly, helpful, and concise response."""

            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.1-8b-instant"
            )
            return chat_completion.choices[0].message.content

        except Exception as e:
            print("Groq Error:", e)
            return f"Sorry, I couldn't process your request right now. Please try again later."

    @app.route("/chatbot", methods=["POST"])
    def chatbot():
        data = request.get_json() or {}
        user_message = data.get("message", "").strip()
        if not user_message:
            return jsonify({"response": "Please ask me something about the books!"}), 400

        books_db = Book.query.all()
        books = [
            {
                "title": b.title,
                "author": b.author,
                "year": b.year,
                "genre": b.genre,
                "rating": b.rating,
                "is_bestseller": b.is_bestseller,
                "editions": b.editions,
                "avail_copies": b.avail_copies,
            }
            for b in books_db
        ]

        response = ask_groq_for_books(user_message, books)
        return jsonify({"response": response})

    # ── Frontend ─────────────────────────────────────────────────────
    @app.route('/')
    def index():
        return render_template('index.html')

    # ── DASHBOARD ────────────────────────────────────────────────────
    @app.route('/api/dashboard')
    def dashboard():
        today = date.today()

        total_books   = Book.query.count()
        total_members = Member.query.filter_by(is_active=True).count()
        borrowed      = Transaction.query.filter_by(status='borrowed').count()
        overdue_q     = [t for t in Transaction.query.filter_by(return_date=None).all()
                         if today > t.due_date]
        overdue       = len(overdue_q)

        chart = []
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            cnt = Transaction.query.filter(Transaction.borrow_date == d).count()
            chart.append({'date': d.isoformat(), 'count': cnt})

        recent = [t.to_dict() for t in
                  Transaction.query.order_by(Transaction.created_at.desc()).limit(10).all()]

        genres = db.session.query(
            Book.genre, func.count(Book.id).label('count')
        ).filter(Book.genre.isnot(None)).group_by(Book.genre)\
         .order_by(func.count(Book.id).desc()).limit(5).all()

        return jsonify({
            'stats': {
                'total_books':   total_books,
                'total_members': total_members,
                'borrowed':      borrowed,
                'overdue':       overdue,
            },
            'chart':   chart,
            'recent':  recent,
            'genres':  [{'genre': g, 'count': c} for g, c in genres],
        })

    # ── BOOKS ────────────────────────────────────────────────────────
    @app.route('/api/books', methods=['GET'])
    def list_books():
        q      = request.args.get('q', '').strip()
        genre  = request.args.get('genre', '').strip()
        avail  = request.args.get('available', '').strip()
        page   = int(request.args.get('page', 1))
        per    = int(request.args.get('per_page', 20))

        query = Book.query
        if q:
            like = f'%{q}%'
            query = query.filter(or_(
                Book.title.ilike(like),
                Book.author.ilike(like),
                Book.isbn.ilike(like),
                Book.genre.ilike(like),
            ))
        if genre:
            query = query.filter(Book.genre.ilike(f'%{genre}%'))
        if avail == 'true':
            query = query.filter(Book.avail_copies > 0)

        total   = query.count()
        books   = query.order_by(Book.created_at.desc())\
                       .offset((page - 1) * per).limit(per).all()
        return jsonify({
            'books': [b.to_dict() for b in books],
            'total': total, 'page': page, 'per_page': per,
        })

    @app.route('/api/books', methods=['POST'])
    def add_book():
        data = request.get_json() or {}
        errors = {}
        if not data.get('title'): errors['title'] = 'Title is required'
        if not data.get('author'): errors['author'] = 'Author is required'
        if errors:
            return jsonify({'errors': errors}), 422

        copies = int(data.get('total_copies') or 1)
        rating_val = data.get('rating')
        if rating_val is not None and rating_val != '':
            rating_val = float(rating_val)
            rating_val = max(0.0, min(5.0, rating_val))
        else:
            rating_val = None

        book = Book(
            title         = data['title'].strip(),
            author        = data['author'].strip(),
            isbn          = data.get('isbn', '').strip() or None,
            genre         = data.get('genre', '').strip() or None,
            publisher     = data.get('publisher', '').strip() or None,
            year          = int(data['year']) if data.get('year') else None,
            total_copies  = copies,
            avail_copies  = copies,
            description   = data.get('description', '').strip() or None,
            cover_color   = data.get('cover_color', '#c9a84c'),
            rating        = rating_val,
            is_bestseller = bool(data.get('is_bestseller', False)),
            editions      = int(data['editions']) if data.get('editions') else None,
        )
        db.session.add(book)
        db.session.commit()
        return jsonify(book.to_dict()), 201

    @app.route('/api/books/<int:bid>', methods=['GET'])
    def get_book(bid):
        book = Book.query.get_or_404(bid)
        return jsonify(book.to_dict())

    @app.route('/api/books/<int:bid>/chapters', methods=['GET'])
    def book_chapters_route(bid):
        book = Book.query.get_or_404(bid)
        data = get_book_chapters(book)
        return jsonify({
            'book_id':       bid,
            'title':         book.title,
            'author':        book.author,
            'pages':         data['pages'],
            'chapters':      data['chapters'],
            'chapter_count': len(data['chapters']),
        })

    @app.route('/api/books/<int:bid>', methods=['PUT'])
    def update_book(bid):
        book = Book.query.get_or_404(bid)
        data = request.get_json() or {}
        errors = {}
        if 'title' in data and not data['title']: errors['title'] = 'Title is required'
        if 'author' in data and not data['author']: errors['author'] = 'Author is required'
        if errors:
            return jsonify({'errors': errors}), 422

        if 'title'         in data: book.title       = data['title'].strip()
        if 'author'        in data: book.author       = data['author'].strip()
        if 'isbn'          in data: book.isbn         = data['isbn'].strip() or None
        if 'genre'         in data: book.genre        = data['genre'].strip() or None
        if 'publisher'     in data: book.publisher    = data['publisher'].strip() or None
        if 'year'          in data: book.year         = int(data['year']) if data['year'] else None
        if 'description'   in data: book.description  = data['description'].strip() or None
        if 'cover_color'   in data: book.cover_color  = data['cover_color']
        if 'is_bestseller' in data: book.is_bestseller = bool(data['is_bestseller'])
        if 'editions'      in data:
            book.editions = int(data['editions']) if data['editions'] else None
        if 'rating' in data:
            rv = data['rating']
            if rv is not None and rv != '':
                book.rating = max(0.0, min(5.0, float(rv)))
            else:
                book.rating = None
        if 'total_copies' in data:
            new_total = int(data['total_copies'])
            diff = new_total - book.total_copies
            book.avail_copies = max(0, book.avail_copies + diff)
            book.total_copies = new_total

        db.session.commit()
        return jsonify(book.to_dict())

    @app.route('/api/books/<int:bid>', methods=['DELETE'])
    def delete_book(bid):
        book = Book.query.get_or_404(bid)
        active = Transaction.query.filter_by(book_id=bid, return_date=None).count()
        if active:
            return jsonify({'error': 'Cannot delete: book has active borrows'}), 409
        db.session.delete(book)
        db.session.commit()
        return jsonify({'deleted': bid})

    @app.route('/api/genres')
    def genres():
        rows = db.session.query(Book.genre)\
                         .filter(Book.genre.isnot(None))\
                         .distinct().all()
        return jsonify([r[0] for r in rows])

    # ── TRENDING SHELVES (OTT-style) ─────────────────────────────────
    @app.route('/api/trending')
    def trending():
        trending_raw = db.session.query(
            Book, func.count(Transaction.id).label('borrow_count')
        ).outerjoin(Transaction, Transaction.book_id == Book.id)\
         .group_by(Book.id)\
         .order_by(func.count(Transaction.id).desc(), Book.rating.desc())\
         .limit(14).all()
        trending_books = [b.to_dict() for b, _ in trending_raw]

        top_rated   = Book.query.filter(Book.rating.isnot(None)).order_by(Book.rating.desc()).limit(14).all()
        bestsellers = Book.query.filter_by(is_bestseller=True).order_by(Book.rating.desc()).limit(14).all()
        new_arrivals = Book.query.order_by(Book.created_at.desc()).limit(14).all()
        adventures  = Book.query.filter(Book.genre.in_(['Fantasy', 'Sci-Fi'])).order_by(Book.rating.desc()).limit(14).all()
        dark        = Book.query.filter(Book.genre.in_(['Mystery', 'Thriller', 'Horror'])).order_by(Book.rating.desc()).limit(14).all()
        mind        = Book.query.filter(Book.genre.in_(['Self-Help', 'Psychology', 'Science', 'Philosophy'])).order_by(Book.rating.desc()).limit(14).all()
        classics    = Book.query.filter(Book.genre.in_(['Classics', 'Biography', 'History'])).order_by(Book.rating.desc()).limit(14).all()

        shelves = []
        def add_shelf(sid, label, sub, books):
            if books:
                shelves.append({'id': sid, 'label': label, 'sublabel': sub,
                                'books': [b if isinstance(b, dict) else b.to_dict() for b in books]})

        add_shelf('trending',    '🔥 Trending Now',       'Most borrowed in your library',   trending_books)
        add_shelf('top_rated',   '⭐ Top Rated',           'Highest rated by readers',         [b.to_dict() for b in top_rated])
        add_shelf('bestsellers', '🏆 Bestsellers',         'Books everyone is talking about',  [b.to_dict() for b in bestsellers])
        add_shelf('new',         '🆕 New Arrivals',        'Recently added to the collection', [b.to_dict() for b in new_arrivals])
        add_shelf('adventures',  '🌍 Epic Adventures',     'Fantasy & Sci-Fi journeys',        [b.to_dict() for b in adventures])
        add_shelf('dark',        '🕵️ Dark & Thrilling',   'Mystery, Thriller & Horror',       [b.to_dict() for b in dark])
        add_shelf('mind',        '🧠 Mind Expanding',      'Science, Self-Help & Philosophy',  [b.to_dict() for b in mind])
        add_shelf('classics',    '📜 Timeless Classics',   'Literature & Biography',           [b.to_dict() for b in classics])
        return jsonify({'shelves': shelves})

    # ── MEMBERS ──────────────────────────────────────────────────────
    @app.route('/api/members', methods=['GET'])
    def list_members():
        q    = request.args.get('q', '').strip()
        page = int(request.args.get('page', 1))
        per  = int(request.args.get('per_page', 20))

        query = Member.query
        if q:
            like = f'%{q}%'
            query = query.filter(or_(
                Member.name.ilike(like),
                Member.email.ilike(like),
                Member.phone.ilike(like),
            ))

        total   = query.count()
        members = query.order_by(Member.created_at.desc())\
                       .offset((page - 1) * per).limit(per).all()
        return jsonify({
            'members': [m.to_dict() for m in members],
            'total': total,
        })

    @app.route('/api/members', methods=['POST'])
    def add_member():
        data = request.get_json() or {}
        errors = {}
        if not data.get('name'):  errors['name']  = 'Name is required'
        if not data.get('email'): errors['email'] = 'Email is required'
        if errors:
            return jsonify({'errors': errors}), 422

        if Member.query.filter_by(email=data['email'].strip()).first():
            return jsonify({'errors': {'email': 'Email already registered'}}), 422

        member = Member(
            name    = data['name'].strip(),
            email   = data['email'].strip().lower(),
            phone   = data.get('phone', '').strip() or None,
            address = data.get('address', '').strip() or None,
        )
        db.session.add(member)
        db.session.commit()
        return jsonify(member.to_dict()), 201

    @app.route('/api/members/<int:mid>', methods=['GET'])
    def get_member(mid):
        member = Member.query.get_or_404(mid)
        data = member.to_dict()
        data['transactions'] = [t.to_dict() for t in
            Transaction.query.filter_by(member_id=mid)
                             .order_by(Transaction.created_at.desc()).all()]
        return jsonify(data)

    @app.route('/api/members/<int:mid>', methods=['PUT'])
    def update_member(mid):
        member = Member.query.get_or_404(mid)
        data = request.get_json() or {}
        if 'name'      in data: member.name      = data['name'].strip()
        if 'phone'     in data: member.phone     = data['phone'].strip() or None
        if 'address'   in data: member.address   = data['address'].strip() or None
        if 'is_active' in data: member.is_active = bool(data['is_active'])
        db.session.commit()
        return jsonify(member.to_dict())

    @app.route('/api/members/<int:mid>', methods=['DELETE'])
    def delete_member(mid):
        member = Member.query.get_or_404(mid)
        active = Transaction.query.filter_by(member_id=mid, return_date=None).count()
        if active:
            return jsonify({'error': 'Member has unreturned books'}), 409
        db.session.delete(member)
        db.session.commit()
        return jsonify({'deleted': mid})

    # ── TRANSACTIONS ─────────────────────────────────────────────────
    @app.route('/api/transactions', methods=['GET'])
    def list_transactions():
        status    = request.args.get('status', '')
        member_id = request.args.get('member_id', '')
        book_id   = request.args.get('book_id', '')
        page      = int(request.args.get('page', 1))
        per       = int(request.args.get('per_page', 20))

        query = Transaction.query
        if member_id: query = query.filter_by(member_id=int(member_id))
        if book_id:   query = query.filter_by(book_id=int(book_id))

        all_txns = query.order_by(Transaction.created_at.desc()).all()

        if status:
            all_txns = [t for t in all_txns if t.compute_status() == status]

        total = len(all_txns)
        page_txns = all_txns[(page - 1) * per: page * per]
        return jsonify({
            'transactions': [t.to_dict() for t in page_txns],
            'total': total,
        })

    @app.route('/api/transactions/borrow', methods=['POST'])
    def borrow_book():
        data      = request.get_json() or {}
        book_id   = data.get('book_id')
        member_id = data.get('member_id')
        days      = int(data.get('days', 14))
        notes     = data.get('notes', '')

        if not book_id or not member_id:
            return jsonify({'error': 'book_id and member_id required'}), 422

        book   = Book.query.get_or_404(book_id)
        member = Member.query.get_or_404(member_id)

        if book.avail_copies < 1:
            return jsonify({'error': 'No copies available'}), 409
        if not member.is_active:
            return jsonify({'error': 'Member account is inactive'}), 409

        existing = Transaction.query.filter_by(
            book_id=book_id, member_id=member_id, return_date=None).first()
        if existing:
            return jsonify({'error': 'Member already has this book borrowed'}), 409

        txn = Transaction(
            book_id   = book_id,
            member_id = member_id,
            due_date  = date.today() + timedelta(days=days),
            notes     = notes.strip() or None,
        )
        book.avail_copies -= 1
        db.session.add(txn)
        db.session.commit()
        return jsonify(txn.to_dict()), 201

    @app.route('/api/transactions/<int:tid>/return', methods=['POST'])
    def return_book(tid):
        txn = Transaction.query.get_or_404(tid)
        if txn.return_date:
            return jsonify({'error': 'Book already returned'}), 409

        txn.return_date = date.today()
        txn.status      = 'returned'
        txn.fine_amount = txn.compute_fine()
        txn.book.avail_copies = min(txn.book.total_copies,
                                    txn.book.avail_copies + 1)
        db.session.commit()
        return jsonify(txn.to_dict())

    @app.route('/api/transactions/<int:tid>', methods=['DELETE'])
    def delete_transaction(tid):
        txn = Transaction.query.get_or_404(tid)
        if not txn.return_date:
            txn.book.avail_copies = min(txn.book.total_copies,
                                        txn.book.avail_copies + 1)
        db.session.delete(txn)
        db.session.commit()
        return jsonify({'deleted': tid})

    # ── SEARCH (all) ─────────────────────────────────────────────────
    @app.route('/api/search')
    def global_search():
        q = request.args.get('q', '').strip()
        if not q:
            return jsonify({'books': [], 'members': []})
        like = f'%{q}%'
        books = Book.query.filter(or_(
            Book.title.ilike(like), Book.author.ilike(like)
        )).limit(5).all()
        members = Member.query.filter(or_(
            Member.name.ilike(like), Member.email.ilike(like)
        )).limit(5).all()
        return jsonify({
            'books':   [b.to_dict() for b in books],
            'members': [m.to_dict() for m in members],
        })

    return app


# ── SEED DATA ────────────────────────────────────────────────────────
def seed_demo_data():
    # Use title-based deduplication so new books are added to existing DBs
    existing_titles = {b.title for b in Book.query.all()}

    books = [
        # ── Fiction ──────────────────────────────────────────────────
        {'title':'The Great Gatsby','author':'F. Scott Fitzgerald','genre':'Fiction','year':1925,'isbn':'978-0-7432-7356-5','total_copies':3,'cover_color':'#4a7c6a','rating':4.1,'is_bestseller':True,'editions':5,'description':'A portrait of the Jazz Age in all of its decadence and excess.'},
        {'title':'To Kill a Mockingbird','author':'Harper Lee','genre':'Fiction','year':1960,'isbn':'978-0-06-112008-4','total_copies':4,'cover_color':'#8b2635','rating':4.8,'is_bestseller':True,'editions':4,'description':'A gripping tale of racial injustice and childhood innocence in the American South.'},
        {'title':'The Alchemist','author':'Paulo Coelho','genre':'Fiction','year':1988,'isbn':'978-0-06-231609-7','total_copies':3,'cover_color':'#c9a84c','rating':4.2,'is_bestseller':True,'editions':4,'description':'A philosophical novel about following your dreams and listening to your heart.'},
        {'title':'The Catcher in the Rye','author':'J.D. Salinger','genre':'Fiction','year':1951,'isbn':'978-0-316-76948-0','total_copies':3,'cover_color':'#b7410e','rating':3.9,'is_bestseller':True,'editions':5,'description':'Holden Caulfield navigates alienation and loss of innocence in 1950s New York City.'},
        {'title':'Of Mice and Men','author':'John Steinbeck','genre':'Fiction','year':1937,'isbn':'978-0-14-028862-8','total_copies':3,'cover_color':'#6d4c41','rating':4.0,'is_bestseller':True,'editions':4,'description':'Two displaced ranch workers chase an impossible dream during the Great Depression.'},
        {'title':'The Kite Runner','author':'Khaled Hosseini','genre':'Fiction','year':2003,'isbn':'978-1-59448-000-3','total_copies':4,'cover_color':'#1a6b3a','rating':4.4,'is_bestseller':True,'editions':3,'description':'A powerful story of friendship, betrayal, and redemption set in Afghanistan.'},
        {'title':'A Thousand Splendid Suns','author':'Khaled Hosseini','genre':'Fiction','year':2007,'isbn':'978-1-59448-950-1','total_copies':3,'cover_color':'#7b3a2a','rating':4.7,'is_bestseller':True,'editions':2,'description':'An unforgettable portrayal of the lives of two Afghan women across three decades of war.'},
        {'title':'The Road','author':'Cormac McCarthy','genre':'Fiction','year':2006,'isbn':'978-0-307-26543-2','total_copies':2,'cover_color':'#455a64','rating':4.1,'is_bestseller':True,'editions':2,'description':'A father and son journey through a post-apocalyptic wasteland, clinging to hope.'},
        {'title':'One Hundred Years of Solitude','author':'Gabriel García Márquez','genre':'Fiction','year':1967,'isbn':'978-0-06-088328-7','total_copies':3,'cover_color':'#4e342e','rating':4.3,'is_bestseller':True,'editions':6,'description':'The Buendía family saga across seven generations in the mythical town of Macondo.'},
        {'title':'The Bell Jar','author':'Sylvia Plath','genre':'Fiction','year':1963,'isbn':'978-0-06-084763-3','total_copies':2,'cover_color':'#546e7a','rating':4.1,'is_bestseller':False,'editions':3,'description':'A semi-autobiographical novel about a young woman\'s descent into mental illness.'},
        {'title':'Norwegian Wood','author':'Haruki Murakami','genre':'Fiction','year':1987,'isbn':'978-0-375-70402-1','total_copies':3,'cover_color':'#2e7d32','rating':4.0,'is_bestseller':True,'editions':3,'description':'A nostalgic story of loss and sexuality set in 1960s Tokyo.'},
        {'title':'Siddhartha','author':'Hermann Hesse','genre':'Fiction','year':1922,'isbn':'978-0-553-20884-2','total_copies':3,'cover_color':'#f57f17','rating':4.3,'is_bestseller':True,'editions':5,'description':'The spiritual journey of a young Indian man during the time of Gautama Buddha.'},
        {'title':'The Picture of Dorian Gray','author':'Oscar Wilde','genre':'Fiction','year':1890,'isbn':'978-0-14-143957-0','total_copies':3,'cover_color':'#880e4f','rating':4.2,'is_bestseller':False,'editions':6,'description':'A vain young man sells his soul for eternal youth while his portrait ages in his place.'},
        {'title':'Life of Pi','author':'Yann Martel','genre':'Fiction','year':2001,'isbn':'978-0-15-602732-3','total_copies':4,'cover_color':'#0277bd','rating':4.2,'is_bestseller':True,'editions':3,'description':'A boy stranded in the Pacific Ocean on a lifeboat with a Bengal tiger tells a remarkable story.'},
        {'title':'Kafka on the Shore','author':'Haruki Murakami','genre':'Fiction','year':2002,'isbn':'978-1-400-04366-3','total_copies':2,'cover_color':'#37474f','rating':4.2,'is_bestseller':True,'editions':2,'description':'A dreamlike narrative blending two stories: a teenage runaway and an old man who can talk to cats.'},
        {'title':'The Remains of the Day','author':'Kazuo Ishiguro','genre':'Fiction','year':1989,'isbn':'978-0-679-73172-5','total_copies':2,'cover_color':'#5d4037','rating':4.1,'is_bestseller':False,'editions':3,'description':'An English butler reflects on years of devoted service and the question of a life well spent.'},

        # ── Dystopian ─────────────────────────────────────────────────
        {'title':'1984','author':'George Orwell','genre':'Dystopian','year':1949,'isbn':'978-0-452-28423-4','total_copies':5,'cover_color':'#2c3e50','rating':4.7,'is_bestseller':True,'editions':6,'description':'A chilling depiction of a totalitarian society where Big Brother watches everything.'},
        {'title':'Brave New World','author':'Aldous Huxley','genre':'Dystopian','year':1932,'isbn':'978-0-06-085052-4','total_copies':3,'cover_color':'#34495e','rating':4.1,'is_bestseller':False,'editions':4,'description':'A futuristic society built on pleasure, conformity and the suppression of individuality.'},
        {'title':'Fahrenheit 451','author':'Ray Bradbury','genre':'Dystopian','year':1953,'isbn':'978-1-451-67331-9','total_copies':3,'cover_color':'#bf360c','rating':4.2,'is_bestseller':True,'editions':5,'description':'In a future America, firemen burn books and one fireman begins to question everything.'},
        {'title':'The Handmaid\'s Tale','author':'Margaret Atwood','genre':'Dystopian','year':1985,'isbn':'978-0-385-49081-8','total_copies':4,'cover_color':'#b71c1c','rating':4.4,'is_bestseller':True,'editions':4,'description':'In the totalitarian Republic of Gilead, fertile women are enslaved as reproductive vessels.'},
        {'title':'Animal Farm','author':'George Orwell','genre':'Dystopian','year':1945,'isbn':'978-0-452-28424-1','total_copies':4,'cover_color':'#558b2f','rating':4.3,'is_bestseller':True,'editions':7,'description':'A allegorical novella where farm animals overthrow their human master, only to face a new tyranny.'},
        {'title':'Never Let Me Go','author':'Kazuo Ishiguro','genre':'Dystopian','year':2005,'isbn':'978-1-400-04339-7','total_copies':2,'cover_color':'#4a148c','rating':4.0,'is_bestseller':False,'editions':2,'description':'Students at a seemingly idyllic English boarding school slowly learn the truth of their existence.'},

        # ── Romance ───────────────────────────────────────────────────
        {'title':'Pride and Prejudice','author':'Jane Austen','genre':'Romance','year':1813,'isbn':'978-0-14-143951-8','total_copies':3,'cover_color':'#c0392b','rating':4.5,'is_bestseller':True,'editions':8,'description':'A witty exploration of love, class and marriage in Regency-era England.'},
        {'title':'Me Before You','author':'Jojo Moyes','genre':'Romance','year':2012,'isbn':'978-0-14-312454-1','total_copies':3,'cover_color':'#e91e63','rating':4.3,'is_bestseller':True,'editions':2,'description':'A heartbreaking love story about a woman who changes the life of a quadriplegic man.'},
        {'title':'Jane Eyre','author':'Charlotte Brontë','genre':'Romance','year':1847,'isbn':'978-0-14-144114-6','total_copies':3,'cover_color':'#ad1457','rating':4.4,'is_bestseller':True,'editions':9,'description':'An orphaned governess falls for the brooding Mr Rochester in this gothic romance.'},
        {'title':'The Notebook','author':'Nicholas Sparks','genre':'Romance','year':1996,'isbn':'978-0-446-60523-5','total_copies':4,'cover_color':'#ec407a','rating':4.1,'is_bestseller':True,'editions':3,'description':'An elderly man reads a love story from a notebook to a woman with dementia — his own story.'},
        {'title':'It Ends with Us','author':'Colleen Hoover','genre':'Romance','year':2016,'isbn':'978-1-501-15622-2','total_copies':4,'cover_color':'#e53935','rating':4.5,'is_bestseller':True,'editions':2,'description':'A young woman falls for a brilliant neurosurgeon, but history begins to repeat itself.'},
        {'title':'Outlander','author':'Diana Gabaldon','genre':'Romance','year':1991,'isbn':'978-0-440-42421-2','total_copies':3,'cover_color':'#6a1b9a','rating':4.3,'is_bestseller':True,'editions':4,'description':'A WWII nurse is swept back to 18th-century Scotland and caught between two very different men.'},
        {'title':'Sense and Sensibility','author':'Jane Austen','genre':'Romance','year':1811,'isbn':'978-0-14-143966-2','total_copies':3,'cover_color':'#d81b60','rating':4.2,'is_bestseller':True,'editions':7,'description':'Two sisters navigate love and heartbreak in early 19th-century England.'},

        # ── Fantasy ───────────────────────────────────────────────────
        {'title':'The Hobbit','author':'J.R.R. Tolkien','genre':'Fantasy','year':1937,'isbn':'978-0-547-92822-7','total_copies':4,'cover_color':'#27ae60','rating':4.6,'is_bestseller':True,'editions':7,'description':'Bilbo Baggins is swept into an epic quest to reclaim the lost dwarf kingdom of Erebor.'},
        {'title':"Harry Potter and the Philosopher's Stone",'author':'J.K. Rowling','genre':'Fantasy','year':1997,'isbn':'978-0-7475-3269-9','total_copies':6,'cover_color':'#8e44ad','rating':4.9,'is_bestseller':True,'editions':3,'description':'A young boy discovers he is a wizard and begins his education at Hogwarts.'},
        {'title':'The Name of the Wind','author':'Patrick Rothfuss','genre':'Fantasy','year':2007,'isbn':'978-0-7564-0407-9','total_copies':3,'cover_color':'#16a085','rating':4.5,'is_bestseller':False,'editions':2,'description':'The tale of a legendary wizard told in his own words — a story of love, loss, and magic.'},
        {'title':'A Game of Thrones','author':'George R.R. Martin','genre':'Fantasy','year':1996,'isbn':'978-0-553-57340-3','total_copies':4,'cover_color':'#1b1b2f','rating':4.7,'is_bestseller':True,'editions':5,'description':'Noble families battle for the Iron Throne of the Seven Kingdoms in this epic fantasy.'},
        {'title':'The Way of Kings','author':'Brandon Sanderson','genre':'Fantasy','year':2010,'isbn':'978-0-7653-2637-9','total_copies':3,'cover_color':'#1a237e','rating':4.6,'is_bestseller':True,'editions':2,'description':'On a world ravaged by storm and war, a young soldier discovers a secret that will change everything.'},
        {'title':'American Gods','author':'Neil Gaiman','genre':'Fantasy','year':2001,'isbn':'978-0-380-97365-0','total_copies':3,'cover_color':'#263238','rating':4.3,'is_bestseller':True,'editions':3,'description':'A recently released convict is drawn into a battle between old gods and new.'},
        {'title':'Good Omens','author':'Terry Pratchett & Neil Gaiman','genre':'Fantasy','year':1990,'isbn':'978-0-060-85398-3','total_copies':3,'cover_color':'#f9a825','rating':4.5,'is_bestseller':True,'editions':4,'description':'An angel and a demon reluctantly team up to prevent the apocalypse in this irreverent comedy.'},
        {'title':'The Night Circus','author':'Erin Morgenstern','genre':'Fantasy','year':2011,'isbn':'978-0-385-53463-5','total_copies':3,'cover_color':'#212121','rating':4.2,'is_bestseller':True,'editions':2,'description':'Two young magicians are pitted against each other in a mysterious contest set inside a magical circus.'},
        {'title':'The Fellowship of the Ring','author':'J.R.R. Tolkien','genre':'Fantasy','year':1954,'isbn':'978-0-618-57494-1','total_copies':4,'cover_color':'#1b5e20','rating':4.8,'is_bestseller':True,'editions':10,'description':'A hobbit and his companions set out on a journey to destroy the One Ring and save Middle-earth.'},
        {'title':'Eragon','author':'Christopher Paolini','genre':'Fantasy','year':2003,'isbn':'978-0-375-82668-5','total_copies':3,'cover_color':'#1565c0','rating':3.9,'is_bestseller':True,'editions':3,'description':'A young farm boy becomes a Dragon Rider and must rise to face an evil king.'},

        # ── History ───────────────────────────────────────────────────
        {'title':'Sapiens','author':'Yuval Noah Harari','genre':'History','year':2011,'isbn':'978-0-06-231609-8','total_copies':2,'cover_color':'#e67e22','rating':4.4,'is_bestseller':True,'editions':2,'description':'A brief history of humankind, from the Stone Age to the modern era.'},
        {'title':'Guns, Germs, and Steel','author':'Jared Diamond','genre':'History','year':1997,'isbn':'978-0-393-31755-8','total_copies':2,'cover_color':'#d68910','rating':4.2,'is_bestseller':True,'editions':3,'description':'Why did some civilisations conquer others? A sweeping account of human history.'},
        {'title':'The Diary of a Young Girl','author':'Anne Frank','genre':'History','year':1947,'isbn':'978-0-553-57712-8','total_copies':4,'cover_color':'#6d4c41','rating':4.7,'is_bestseller':True,'editions':8,'description':'Anne Frank\'s extraordinary diary written while hiding from the Nazis in Amsterdam.'},
        {'title':'Homo Deus','author':'Yuval Noah Harari','genre':'History','year':2015,'isbn':'978-0-062-44214-2','total_copies':3,'cover_color':'#bf360c','rating':4.2,'is_bestseller':True,'editions':2,'description':'A brief history of tomorrow — what will become of humanity as technology surpasses us?'},
        {'title':'21 Lessons for the 21st Century','author':'Yuval Noah Harari','genre':'History','year':2018,'isbn':'978-0-525-51217-5','total_copies':2,'cover_color':'#4a148c','rating':4.1,'is_bestseller':True,'editions':2,'description':'How do we make sense of a world that is more complex and confusing than ever before?'},
        {'title':'SPQR: A History of Ancient Rome','author':'Mary Beard','genre':'History','year':2015,'isbn':'978-1-631-49484-8','total_copies':2,'cover_color':'#795548','rating':4.3,'is_bestseller':False,'editions':2,'description':'A groundbreaking history of ancient Rome that challenges how we understand the world\'s first global empire.'},

        # ── Self-Help ─────────────────────────────────────────────────
        {'title':'Atomic Habits','author':'James Clear','genre':'Self-Help','year':2018,'isbn':'978-0-7352-1129-2','total_copies':4,'cover_color':'#1abc9c','rating':4.8,'is_bestseller':True,'editions':2,'description':'An easy and proven way to build good habits and break bad ones.'},
        {'title':'The 7 Habits of Highly Effective People','author':'Stephen R. Covey','genre':'Self-Help','year':1989,'isbn':'978-0-7432-6951-3','total_copies':3,'cover_color':'#148f77','rating':4.4,'is_bestseller':True,'editions':5,'description':'Powerful lessons in personal change based on timeless principles.'},
        {'title':'The Power of Now','author':'Eckhart Tolle','genre':'Self-Help','year':1997,'isbn':'978-1-577-31480-6','total_copies':3,'cover_color':'#00838f','rating':4.3,'is_bestseller':True,'editions':4,'description':'A guide to spiritual enlightenment that teaches living fully in the present moment.'},
        {'title':'How to Win Friends and Influence People','author':'Dale Carnegie','genre':'Self-Help','year':1936,'isbn':'978-0-671-72765-5','total_copies':4,'cover_color':'#0d47a1','rating':4.4,'is_bestseller':True,'editions':8,'description':'Timeless advice on communication, persuasion, and human relations still relevant today.'},
        {'title':'Think and Grow Rich','author':'Napoleon Hill','genre':'Self-Help','year':1937,'isbn':'978-1-585-42433-9','total_copies':3,'cover_color':'#f57c00','rating':4.2,'is_bestseller':True,'editions':7,'description':'Thirteen principles of personal achievement distilled from interviews with 500 successful people.'},
        {'title':'The Subtle Art of Not Giving a F*ck','author':'Mark Manson','genre':'Self-Help','year':2016,'isbn':'978-0-062-45773-3','total_copies':4,'cover_color':'#e65100','rating':4.1,'is_bestseller':True,'editions':3,'description':'A counterintuitive approach to living a good life by embracing your limitations.'},
        {'title':'Deep Work','author':'Cal Newport','genre':'Self-Help','year':2016,'isbn':'978-1-455-58669-1','total_copies':3,'cover_color':'#1a237e','rating':4.4,'is_bestseller':True,'editions':2,'description':'Rules for focused success in a distracted world — the ability to focus is becoming rare and valuable.'},
        {'title':'Ikigai','author':'Héctor García & Francesc Miralles','genre':'Self-Help','year':2016,'isbn':'978-0-143-13021-3','total_copies':3,'cover_color':'#e8a838','rating':4.2,'is_bestseller':True,'editions':3,'description':'The Japanese secret to a long and happy life — finding purpose at the intersection of passion, mission, and vocation.'},
        {'title':'Can\'t Hurt Me','author':'David Goggins','genre':'Self-Help','year':2018,'isbn':'978-1-544-51536-3','total_copies':3,'cover_color':'#212121','rating':4.6,'is_bestseller':True,'editions':2,'description':'Master your mind and defy the odds — the story of an extraordinary man\'s journey to push past limits.'},

        # ── Sci-Fi ────────────────────────────────────────────────────
        {'title':'Dune','author':'Frank Herbert','genre':'Sci-Fi','year':1965,'isbn':'978-0-441-17271-9','total_copies':3,'cover_color':'#d35400','rating':4.3,'is_bestseller':False,'editions':5,'description':'A sweeping tale of politics, religion, ecology and power on a desert planet.'},
        {'title':"The Hitchhiker's Guide to the Galaxy",'author':'Douglas Adams','genre':'Sci-Fi','year':1979,'isbn':'978-0-345-39180-3','total_copies':4,'cover_color':'#2980b9','rating':4.6,'is_bestseller':True,'editions':4,'description':'An absurdly funny journey through space after Earth is demolished for a bypass.'},
        {'title':'Foundation','author':'Isaac Asimov','genre':'Sci-Fi','year':1951,'isbn':'978-0-553-29335-7','total_copies':3,'cover_color':'#1565c0','rating':4.4,'is_bestseller':True,'editions':6,'description':'A mathematician devises a plan to preserve civilisation through a coming dark age spanning millennia.'},
        {'title':"Ender's Game",'author':'Orson Scott Card','genre':'Sci-Fi','year':1985,'isbn':'978-0-812-55070-9','total_copies':3,'cover_color':'#1b5e20','rating':4.5,'is_bestseller':True,'editions':4,'description':'A gifted boy is trained from childhood to be humanity\'s greatest weapon against an alien threat.'},
        {'title':'The Martian','author':'Andy Weir','genre':'Sci-Fi','year':2011,'isbn':'978-0-553-41802-6','total_copies':4,'cover_color':'#bf360c','rating':4.6,'is_bestseller':True,'editions':3,'description':'An astronaut is stranded on Mars and must use his wits to survive and signal Earth.'},
        {'title':'Project Hail Mary','author':'Andy Weir','genre':'Sci-Fi','year':2021,'isbn':'978-0-593-13520-4','total_copies':3,'cover_color':'#006064','rating':4.8,'is_bestseller':True,'editions':2,'description':'A lone astronaut wakes with no memory millions of miles from Earth — and must save the solar system.'},
        {'title':'Neuromancer','author':'William Gibson','genre':'Sci-Fi','year':1984,'isbn':'978-0-441-56956-4','total_copies':2,'cover_color':'#212121','rating':4.0,'is_bestseller':False,'editions':4,'description':'The founding novel of cyberpunk follows a washed-up hacker hired for one last job in cyberspace.'},
        {'title':'The Left Hand of Darkness','author':'Ursula K. Le Guin','genre':'Sci-Fi','year':1969,'isbn':'978-0-441-47812-5','total_copies':2,'cover_color':'#37474f','rating':4.2,'is_bestseller':False,'editions':5,'description':'A human envoy visits a world where inhabitants have no fixed gender, exploring identity and society.'},

        # ── Mystery ───────────────────────────────────────────────────
        {'title':'The Girl with the Dragon Tattoo','author':'Stieg Larsson','genre':'Mystery','year':2005,'isbn':'978-0-307-45454-1','total_copies':3,'cover_color':'#555555','rating':4.2,'is_bestseller':True,'editions':3,'description':'A journalist and a hacker investigate a decades-old disappearance in a wealthy Swedish family.'},
        {'title':'And Then There Were None','author':'Agatha Christie','genre':'Mystery','year':1939,'isbn':'978-0-06-207348-8','total_copies':4,'cover_color':'#7f8c8d','rating':4.5,'is_bestseller':True,'editions':6,'description':'Ten strangers are lured to an island, and one by one they begin to die.'},
        {'title':'Big Little Lies','author':'Liane Moriarty','genre':'Mystery','year':2014,'isbn':'978-0-399-16707-3','total_copies':3,'cover_color':'#00897b','rating':4.2,'is_bestseller':True,'editions':2,'description':'Three women\'s lives unravel to reveal the dark secrets behind a seemingly perfect community.'},
        {'title':'The Silent Patient','author':'Alex Michaelides','genre':'Mystery','year':2019,'isbn':'978-1-250-30169-7','total_copies':4,'cover_color':'#4527a0','rating':4.3,'is_bestseller':True,'editions':2,'description':'A famous painter shoots her husband five times and then never speaks another word.'},
        {'title':'Murder on the Orient Express','author':'Agatha Christie','genre':'Mystery','year':1934,'isbn':'978-0-062-07350-1','total_copies':3,'cover_color':'#5d4037','rating':4.4,'is_bestseller':True,'editions':8,'description':'Hercule Poirot investigates a murder aboard a snowbound luxury train.'},
        {'title':'Rebecca','author':'Daphne du Maurier','genre':'Mystery','year':1938,'isbn':'978-0-380-73040-7','total_copies':3,'cover_color':'#4a235a','rating':4.3,'is_bestseller':True,'editions':6,'description':'A naive young woman marries a wealthy widower and is haunted by the shadow of his first wife.'},
        {'title':'The Thursday Murder Club','author':'Richard Osman','genre':'Mystery','year':2020,'isbn':'978-1-984-88069-5','total_copies':3,'cover_color':'#1b5e20','rating':4.2,'is_bestseller':True,'editions':2,'description':'Four retirees in a quiet village meet weekly to investigate unsolved crimes — then a real murder occurs.'},
        {'title':'In the Woods','author':'Tana French','genre':'Mystery','year':2007,'isbn':'978-0-143-11380-2','total_copies':2,'cover_color':'#33691e','rating':4.1,'is_bestseller':True,'editions':2,'description':'A detective investigates a murder near the woods where he alone survived a mysterious childhood incident.'},

        # ── Thriller ──────────────────────────────────────────────────
        {'title':'Gone Girl','author':'Gillian Flynn','genre':'Thriller','year':2012,'isbn':'978-0-307-58836-4','total_copies':3,'cover_color':'#c0392b','rating':4.0,'is_bestseller':True,'editions':2,'description':'On their fifth anniversary, Nick Dunne\'s wife Amy disappears — and nothing is what it seems.'},
        {'title':'The Da Vinci Code','author':'Dan Brown','genre':'Thriller','year':2003,'isbn':'978-0-385-50420-5','total_copies':4,'cover_color':'#8b0000','rating':3.9,'is_bestseller':True,'editions':3,'description':'A Harvard symbologist unravels a deadly conspiracy hidden within the works of Leonardo da Vinci.'},
        {'title':'The Girl on the Train','author':'Paula Hawkins','genre':'Thriller','year':2015,'isbn':'978-1-594-63398-8','total_copies':4,'cover_color':'#37474f','rating':4.0,'is_bestseller':True,'editions':2,'description':'A woman commuting daily becomes entangled in the disappearance of a woman she obsessively watched.'},
        {'title':'The Firm','author':'John Grisham','genre':'Thriller','year':1991,'isbn':'978-0-385-41634-3','total_copies':3,'cover_color':'#1a237e','rating':4.0,'is_bestseller':True,'editions':3,'description':'A young lawyer joins a prestigious firm, only to discover it has a deeply dangerous secret.'},
        {'title':'I Am Pilgrim','author':'Terry Hayes','genre':'Thriller','year':2013,'isbn':'978-1-439-17353-9','total_copies':2,'cover_color':'#b71c1c','rating':4.3,'is_bestseller':True,'editions':2,'description':'A retired American intelligence agent is pulled back into action to stop a terrifying bio-attack.'},
        {'title':'The Bourne Identity','author':'Robert Ludlum','genre':'Thriller','year':1980,'isbn':'978-0-553-26011-3','total_copies':3,'cover_color':'#263238','rating':4.1,'is_bestseller':True,'editions':4,'description':'A man pulled from the Mediterranean with no memory must discover who he is before his enemies find him.'},
        {'title':'Angels and Demons','author':'Dan Brown','genre':'Thriller','year':2000,'isbn':'978-0-671-02736-0','total_copies':3,'cover_color':'#4e342e','rating':4.0,'is_bestseller':True,'editions':3,'description':'Robert Langdon races to defuse a ticking time bomb hidden deep in the heart of the Vatican.'},

        # ── Biography ─────────────────────────────────────────────────
        {'title':'Steve Jobs','author':'Walter Isaacson','genre':'Biography','year':2011,'isbn':'978-1-4516-4853-9','total_copies':2,'cover_color':'#95a5a6','rating':4.3,'is_bestseller':True,'editions':2,'description':'The exclusive biography of Apple co-founder Steve Jobs, based on over 40 interviews.'},
        {'title':'Long Walk to Freedom','author':'Nelson Mandela','genre':'Biography','year':1994,'isbn':'978-0-316-54818-3','total_copies':2,'cover_color':'#196f3d','rating':4.7,'is_bestseller':True,'editions':3,'description':'The autobiography of Nelson Mandela — his journey from rural boy to global icon.'},
        {'title':'Becoming','author':'Michelle Obama','genre':'Biography','year':2018,'isbn':'978-1-524-76313-8','total_copies':4,'cover_color':'#880e4f','rating':4.6,'is_bestseller':True,'editions':2,'description':'The deeply personal memoir of the former First Lady of the United States.'},
        {'title':'Elon Musk','author':'Walter Isaacson','genre':'Biography','year':2023,'isbn':'978-1-982-18128-4','total_copies':3,'cover_color':'#0d47a1','rating':4.1,'is_bestseller':True,'editions':1,'description':'The definitive biography of Elon Musk by the author who shadowed him for two years.'},
        {'title':'Leonardo da Vinci','author':'Walter Isaacson','genre':'Biography','year':2017,'isbn':'978-1-501-13983-3','total_copies':2,'cover_color':'#5d4037','rating':4.4,'is_bestseller':True,'editions':2,'description':'The biography of history\'s greatest creative genius, based on his notebooks and art.'},
        {'title':'Open','author':'Andre Agassi','genre':'Biography','year':2009,'isbn':'978-0-307-26816-7','total_copies':2,'cover_color':'#e65100','rating':4.5,'is_bestseller':True,'editions':2,'description':'One of the most honest and riveting autobiographies ever written by a sports icon.'},
        {'title':'I Know Why the Caged Bird Sings','author':'Maya Angelou','genre':'Biography','year':1969,'isbn':'978-0-345-51440-0','total_copies':3,'cover_color':'#4a148c','rating':4.5,'is_bestseller':True,'editions':5,'description':'Maya Angelou\'s coming-of-age memoir of trauma, resilience, and the power of literature.'},

        # ── Philosophy ────────────────────────────────────────────────
        {'title':'Meditations','author':'Marcus Aurelius','genre':'Philosophy','year':180,'isbn':'978-0-14-044140-6','total_copies':3,'cover_color':'#6c5ce7','rating':4.6,'is_bestseller':True,'editions':10,'description':'Personal writings of the Roman emperor reflecting on Stoic philosophy and self-improvement.'},
        {'title':"Sophie's World",'author':'Jostein Gaarder','genre':'Philosophy','year':1991,'isbn':'978-0-374-53087-9','total_copies':2,'cover_color':'#5e35b1','rating':4.1,'is_bestseller':False,'editions':3,'description':'A thrilling journey through the history of philosophy, disguised as a novel.'},
        {'title':'Thus Spoke Zarathustra','author':'Friedrich Nietzsche','genre':'Philosophy','year':1883,'isbn':'978-0-140-44118-5','total_copies':2,'cover_color':'#311b92','rating':4.2,'is_bestseller':False,'editions':8,'description':'Nietzsche\'s philosophical novel introducing the Overman and the eternal recurrence of existence.'},
        {'title':'Beyond Good and Evil','author':'Friedrich Nietzsche','genre':'Philosophy','year':1886,'isbn':'978-0-679-72465-9','total_copies':2,'cover_color':'#1a237e','rating':4.1,'is_bestseller':False,'editions':7,'description':'A critique of past philosophers and a challenge to conventional morality.'},
        {'title':'Letters from a Stoic','author':'Seneca','genre':'Philosophy','year':65,'isbn':'978-0-140-44210-6','total_copies':2,'cover_color':'#4e342e','rating':4.4,'is_bestseller':False,'editions':6,'description':'Moral letters to his young friend Lucilius, covering friendship, loss, wealth, and the good life.'},
        {'title':'The Art of War','author':'Sun Tzu','genre':'Philosophy','year':500,'isbn':'978-0-140-45542-7','total_copies':3,'cover_color':'#c62828','rating':4.2,'is_bestseller':True,'editions':12,'description':'Ancient Chinese military treatise on strategy, tactics, and competition that still resonates today.'},

        # ── Science ───────────────────────────────────────────────────
        {'title':'A Brief History of Time','author':'Stephen Hawking','genre':'Science','year':1988,'isbn':'978-0-553-38016-3','total_copies':3,'cover_color':'#00b894','rating':4.3,'is_bestseller':True,'editions':4,'description':'From the Big Bang to Black Holes — Hawking explains the universe in accessible terms.'},
        {'title':'The Selfish Gene','author':'Richard Dawkins','genre':'Science','year':1976,'isbn':'978-0-19-857519-1','total_copies':2,'cover_color':'#00897b','rating':4.2,'is_bestseller':False,'editions':4,'description':'Dawkins popularises the gene-centred view of evolution in this landmark work.'},
        {'title':'The Gene: An Intimate History','author':'Siddhartha Mukherjee','genre':'Science','year':2016,'isbn':'978-1-476-73352-0','total_copies':2,'cover_color':'#00695c','rating':4.4,'is_bestseller':True,'editions':2,'description':'A sweeping history of the gene and how it has shaped our understanding of humanity.'},
        {'title':'Cosmos','author':'Carl Sagan','genre':'Science','year':1980,'isbn':'978-0-345-53943-4','total_copies':3,'cover_color':'#1a237e','rating':4.5,'is_bestseller':True,'editions':5,'description':'Carl Sagan\'s personal voyage through science, history, and the stars — a timeless classic.'},
        {'title':"Surely You're Joking, Mr. Feynman!",'author':'Richard P. Feynman','genre':'Science','year':1985,'isbn':'978-0-393-31604-9','total_copies':3,'cover_color':'#ef6c00','rating':4.6,'is_bestseller':True,'editions':4,'description':'The irreverent and brilliant adventures of Nobel-winning physicist Richard Feynman.'},
        {'title':'Astrophysics for People in a Hurry','author':'Neil deGrasse Tyson','genre':'Science','year':2017,'isbn':'978-0-393-60939-4','total_copies':3,'cover_color':'#0d47a1','rating':4.2,'is_bestseller':True,'editions':2,'description':'The biggest ideas in the universe explained simply and with great wit.'},
        {'title':'The Body: A Guide for Occupants','author':'Bill Bryson','genre':'Science','year':2019,'isbn':'978-0-385-53968-5','total_copies':3,'cover_color':'#2e7d32','rating':4.3,'is_bestseller':True,'editions':2,'description':'A grand tour of the human body — how it works, its quirks, and what keeps it ticking.'},

        # ── Business ──────────────────────────────────────────────────
        {'title':'Rich Dad Poor Dad','author':'Robert T. Kiyosaki','genre':'Business','year':1997,'isbn':'978-1-61268-116-2','total_copies':4,'cover_color':'#0984e3','rating':4.0,'is_bestseller':True,'editions':4,'description':'What the rich teach their kids about money that the poor and middle class do not.'},
        {'title':'Zero to One','author':'Peter Thiel','genre':'Business','year':2014,'isbn':'978-0-8041-3929-8','total_copies':3,'cover_color':'#1565c0','rating':4.2,'is_bestseller':True,'editions':2,'description':'Notes on startups, or how to build the future — from a legendary Silicon Valley entrepreneur.'},
        {'title':'The Lean Startup','author':'Eric Ries','genre':'Business','year':2011,'isbn':'978-0-307-88789-4','total_copies':3,'cover_color':'#006064','rating':4.3,'is_bestseller':True,'editions':2,'description':'How today\'s entrepreneurs use continuous innovation to build radically successful businesses.'},
        {'title':'Good to Great','author':'Jim Collins','genre':'Business','year':2001,'isbn':'978-0-066-62099-2','total_copies':3,'cover_color':'#0d47a1','rating':4.3,'is_bestseller':True,'editions':3,'description':'Why some companies make the leap to greatness and others don\'t — a five-year study of 1,435 companies.'},
        {'title':'Shoe Dog','author':'Phil Knight','genre':'Business','year':2016,'isbn':'978-1-501-13518-7','total_copies':3,'cover_color':'#e65100','rating':4.6,'is_bestseller':True,'editions':2,'description':'The memoir of Nike\'s founder — a surprisingly honest account of building one of the world\'s most iconic brands.'},
        {'title':'The Hard Thing About Hard Things','author':'Ben Horowitz','genre':'Business','year':2014,'isbn':'978-0-062-27335-5','total_copies':2,'cover_color':'#212121','rating':4.3,'is_bestseller':True,'editions':2,'description':'Building a business when there are no easy answers — by a revered Silicon Valley entrepreneur and investor.'},
        {'title':'Principles: Life and Work','author':'Ray Dalio','genre':'Business','year':2017,'isbn':'978-1-501-12408-2','total_copies':2,'cover_color':'#1a237e','rating':4.2,'is_bestseller':True,'editions':2,'description':'The unconventional principles behind Bridgewater\'s success and Dalio\'s personal philosophy.'},

        # ── Psychology ────────────────────────────────────────────────
        {'title':'Thinking, Fast and Slow','author':'Daniel Kahneman','genre':'Psychology','year':2011,'isbn':'978-0-374-27563-1','total_copies':3,'cover_color':'#a29bfe','rating':4.5,'is_bestseller':True,'editions':2,'description':'A Nobel laureate explores two systems of thought and the psychology of decision-making.'},
        {'title':"Man's Search for Meaning",'author':'Viktor E. Frankl','genre':'Psychology','year':1946,'isbn':'978-0-8070-1428-6','total_copies':3,'cover_color':'#7c4dff','rating':4.8,'is_bestseller':True,'editions':6,'description':'A psychiatrist\'s account of his experiences in Nazi concentration camps and his discovery of logotherapy.'},
        {'title':'The Body Keeps the Score','author':'Bessel van der Kolk','genre':'Psychology','year':2014,'isbn':'978-0-670-78593-3','total_copies':3,'cover_color':'#4527a0','rating':4.7,'is_bestseller':True,'editions':2,'description':'How trauma reshapes body and brain, and the innovative treatments that can offer healing.'},
        {'title':'Flow','author':'Mihaly Csikszentmihalyi','genre':'Psychology','year':1990,'isbn':'978-0-061-33920-2','total_copies':2,'cover_color':'#00838f','rating':4.2,'is_bestseller':True,'editions':3,'description':'The psychology of optimal experience — what makes life worth living?'},
        {'title':'Influence: The Psychology of Persuasion','author':'Robert Cialdini','genre':'Psychology','year':1984,'isbn':'978-0-061-24189-5','total_copies':3,'cover_color':'#bf360c','rating':4.4,'is_bestseller':True,'editions':5,'description':'The definitive guide to the six principles of persuasion used in sales, marketing, and leadership.'},
        {'title':'Emotional Intelligence','author':'Daniel Goleman','genre':'Psychology','year':1995,'isbn':'978-0-553-37506-0','total_copies':2,'cover_color':'#1b5e20','rating':4.1,'is_bestseller':True,'editions':4,'description':'Why emotional intelligence can matter more than IQ in work, relationships, and life.'},

        # ── Horror ────────────────────────────────────────────────────
        {'title':'The Shining','author':'Stephen King','genre':'Horror','year':1977,'isbn':'978-0-307-74365-6','total_copies':3,'cover_color':'#424242','rating':4.4,'is_bestseller':True,'editions':4,'description':'A family heads to an isolated hotel for the winter, where supernatural forces drive the father to madness.'},
        {'title':'It','author':'Stephen King','genre':'Horror','year':1986,'isbn':'978-1-501-14224-0','total_copies':3,'cover_color':'#880e4f','rating':4.5,'is_bestseller':True,'editions':4,'description':'A group of childhood friends are reunited to battle the shapeshifting monster that terrorised them as kids.'},
        {'title':'Dracula','author':'Bram Stoker','genre':'Horror','year':1897,'isbn':'978-0-141-43984-3','total_copies':3,'cover_color':'#b71c1c','rating':4.2,'is_bestseller':True,'editions':9,'description':'The original vampire novel — Count Dracula attempts to move from Transylvania to England to spread the undead curse.'},
        {'title':'Frankenstein','author':'Mary Shelley','genre':'Horror','year':1818,'isbn':'978-0-486-28211-4','total_copies':3,'cover_color':'#212121','rating':4.1,'is_bestseller':True,'editions':10,'description':'A scientist\'s obsession with creating life leads to the birth of a monster and unimaginable consequences.'},

        # ── Classics ──────────────────────────────────────────────────
        {'title':'Crime and Punishment','author':'Fyodor Dostoevsky','genre':'Classics','year':1866,'isbn':'978-0-14-305814-5','total_copies':2,'cover_color':'#795548','rating':4.5,'is_bestseller':False,'editions':8,'description':'A young man commits a murder and grapples with guilt, morality and redemption in 19th-century Russia.'},
        {'title':'Don Quixote','author':'Miguel de Cervantes','genre':'Classics','year':1605,'isbn':'978-0-060-93434-7','total_copies':2,'cover_color':'#e65100','rating':4.2,'is_bestseller':False,'editions':12,'description':'A man driven mad by chivalric romances sets out as a knight-errant to revive chivalry in Spain.'},
        {'title':'Moby Dick','author':'Herman Melville','genre':'Classics','year':1851,'isbn':'978-0-142-43723-9','total_copies':2,'cover_color':'#0d47a1','rating':4.0,'is_bestseller':False,'editions':9,'description':'Captain Ahab\'s monomaniacal quest for revenge against the white whale that took his leg.'},
        {'title':'Anna Karenina','author':'Leo Tolstoy','genre':'Classics','year':1878,'isbn':'978-0-143-10500-5','total_copies':2,'cover_color':'#6a1b9a','rating':4.4,'is_bestseller':True,'editions':8,'description':'A married aristocrat\'s doomed affair with Count Vronsky set against the backdrop of Russian society.'},
        {'title':'War and Peace','author':'Leo Tolstoy','genre':'Classics','year':1869,'isbn':'978-0-307-26693-4','total_copies':2,'cover_color':'#1b5e20','rating':4.3,'is_bestseller':False,'editions':7,'description':'Napoleon\'s invasion of Russia seen through the eyes of five aristocratic families.'},
        {'title':'Great Expectations','author':'Charles Dickens','genre':'Classics','year':1861,'isbn':'978-0-141-43960-7','total_copies':3,'cover_color':'#5d4037','rating':4.2,'is_bestseller':True,'editions':9,'description':'Pip, an orphan, rises from humble origins to high society, discovering that wealth does not bring happiness.'},

        # ── Children ──────────────────────────────────────────────────
        {'title':'The Little Prince','author':'Antoine de Saint-Exupéry','genre':'Children','year':1943,'isbn':'978-0-15-646511-4','total_copies':5,'cover_color':'#ffca28','rating':4.6,'is_bestseller':True,'editions':7,'description':'A poetic tale about a young prince who visits various planets, including Earth, in search of friendship.'},
        {'title':"Charlotte's Web",'author':'E.B. White','genre':'Children','year':1952,'isbn':'978-0-061-96398-4','total_copies':4,'cover_color':'#2e7d32','rating':4.5,'is_bestseller':True,'editions':6,'description':'A spider named Charlotte helps save her friend Wilbur the pig from being slaughtered.'},
        {'title':"Alice's Adventures in Wonderland",'author':'Lewis Carroll','genre':'Children','year':1865,'isbn':'978-0-141-32151-5','total_copies':4,'cover_color':'#7b1fa2','rating':4.3,'is_bestseller':True,'editions':12,'description':'A young girl falls through a rabbit hole into a nonsensical fantasy world.'},
        {'title':'Matilda','author':'Roald Dahl','genre':'Children','year':1988,'isbn':'978-0-142-41009-6','total_copies':4,'cover_color':'#e91e63','rating':4.7,'is_bestseller':True,'editions':5,'description':'A bookish girl with telekinetic powers outwits her awful family and tyrannical headmistress.'},
        {'title':'The BFG','author':'Roald Dahl','genre':'Children','year':1982,'isbn':'978-0-142-41002-7','total_copies':3,'cover_color':'#00838f','rating':4.4,'is_bestseller':True,'editions':4,'description':'A young girl befriends the Big Friendly Giant and together they set out to stop the other giants.'},

        # ── Travel ────────────────────────────────────────────────────
        {'title':'Into the Wild','author':'Jon Krakauer','genre':'Travel','year':1996,'isbn':'978-0-385-48680-4','total_copies':3,'cover_color':'#2e7d32','rating':4.3,'is_bestseller':True,'editions':2,'description':'The story of Christopher McCandless, who abandoned everything to live in the Alaskan wilderness.'},
        {'title':'In a Sunburned Country','author':'Bill Bryson','genre':'Travel','year':2000,'isbn':'978-0-767-90817-8','total_copies':2,'cover_color':'#e65100','rating':4.3,'is_bestseller':False,'editions':2,'description':'Bill Bryson\'s hilarious account of travelling around Australia, the world\'s most fascinating country.'},
        {'title':'A Walk in the Woods','author':'Bill Bryson','genre':'Travel','year':1998,'isbn':'978-0-307-27969-3','total_copies':3,'cover_color':'#388e3c','rating':4.3,'is_bestseller':True,'editions':3,'description':'Bryson and a hapless friend attempt to hike the 2,100-mile Appalachian Trail with hilarious results.'},

        # ── Poetry ────────────────────────────────────────────────────
        {'title':'Milk and Honey','author':'Rupi Kaur','genre':'Poetry','year':2014,'isbn':'978-1-449-47341-4','total_copies':3,'cover_color':'#f9a825','rating':4.2,'is_bestseller':True,'editions':2,'description':'A collection of poetry about survival — about the experience of violence, abuse, love, and loss.'},
        {'title':'The Sun and Her Flowers','author':'Rupi Kaur','genre':'Poetry','year':2017,'isbn':'978-1-449-47352-0','total_copies':3,'cover_color':'#e65100','rating':4.2,'is_bestseller':True,'editions':2,'description':'A journey of wilting, falling, rooting, rising, and blooming — Rupi Kaur\'s second poetry collection.'},

        # ── Cooking ───────────────────────────────────────────────────
        {'title':'Salt Fat Acid Heat','author':'Samin Nosrat','genre':'Cooking','year':2017,'isbn':'978-1-476-75354-2','total_copies':2,'cover_color':'#ef6c00','rating':4.7,'is_bestseller':True,'editions':2,'description':'Master four elements of good cooking and you can cook anything from memory.'},
        {'title':'Jerusalem','author':'Yotam Ottolenghi & Sami Tamimi','genre':'Cooking','year':2012,'isbn':'978-1-607-74329-6','total_copies':2,'cover_color':'#ffd600','rating':4.6,'is_bestseller':True,'editions':3,'description':'A celebration of the rich and diverse food of Jerusalem from two chefs raised on opposite sides of the city.'},

        # ── Art ───────────────────────────────────────────────────────
        {'title':'The Story of Art','author':'E.H. Gombrich','genre':'Art','year':1950,'isbn':'978-0-714-83247-1','total_copies':2,'cover_color':'#880e4f','rating':4.5,'is_bestseller':True,'editions':16,'description':'The world\'s most famous and popular art book — a 700-year journey through Western art.'},
        {'title':'Ways of Seeing','author':'John Berger','genre':'Art','year':1972,'isbn':'978-0-140-13515-8','total_copies':2,'cover_color':'#1a237e','rating':4.3,'is_bestseller':False,'editions':5,'description':'A radical look at how and why we see images, challenging traditional Western approaches to art.'},

        # ── Comics ────────────────────────────────────────────────────
        {'title':'Watchmen','author':'Alan Moore','genre':'Comics','year':1987,'isbn':'978-1-401-24222-7','total_copies':3,'cover_color':'#212121','rating':4.6,'is_bestseller':True,'editions':4,'description':'Superheroes exist but are flawed humans — a deconstruction of the genre set against the Cold War.'},
        {'title':'Maus: A Survivor\'s Tale','author':'Art Spiegelman','genre':'Comics','year':1991,'isbn':'978-0-679-74840-2','total_copies':2,'cover_color':'#4e342e','rating':4.6,'is_bestseller':True,'editions':3,'description':'A Pulitzer-winning graphic novel about a Holocaust survivor, told with mice as Jews and cats as Nazis.'},
        # ── More Comics & Graphic Novels ──────────────────────────────
        {'title':'Persepolis','author':'Marjane Satrapi','genre':'Comics','year':2000,'isbn':'978-0-375-71457-0','total_copies':2,'cover_color':'#263238','rating':4.4,'is_bestseller':True,'editions':3,'description':'The story of a young girl growing up in Iran during the Islamic Revolution, told as a graphic memoir.'},

        # ── More Fiction ──────────────────────────────────────────────
        {'title':'Beloved','author':'Toni Morrison','genre':'Fiction','year':1987,'isbn':'978-1-400-03341-1','total_copies':2,'cover_color':'#4a148c','rating':4.3,'is_bestseller':True,'editions':4,'description':'A former slave is haunted by the spirit of her dead daughter in post-Civil War Ohio.'},
        {'title':'The Color Purple','author':'Alice Walker','genre':'Fiction','year':1982,'isbn':'978-0-156-02834-4','total_copies':2,'cover_color':'#6a1b9a','rating':4.4,'is_bestseller':True,'editions':4,'description':'Two sisters exchange letters spanning decades, surviving abuse and finding strength and love.'},

        # ── More Romance ──────────────────────────────────────────────
        {'title':"The Time Traveler's Wife",'author':'Audrey Niffenegger','genre':'Romance','year':2003,'isbn':'978-0-156-02943-3','total_copies':3,'cover_color':'#3f51b5','rating':4.2,'is_bestseller':True,'editions':3,'description':'A man with a rare genetic disorder travels involuntarily through time and the woman who loves him.'},

        # ── More Fantasy ──────────────────────────────────────────────
        {'title':'Mistborn: The Final Empire','author':'Brandon Sanderson','genre':'Fantasy','year':2006,'isbn':'978-0-765-31178-4','total_copies':3,'cover_color':'#37474f','rating':4.6,'is_bestseller':True,'editions':3,'description':'In a world where ash falls from the sky, a crew of thieves plan to pull off an impossible heist.'},
        {'title':'The Lies of Locke Lamora','author':'Scott Lynch','genre':'Fantasy','year':2006,'isbn':'978-0-553-58894-0','total_copies':2,'cover_color':'#3e2723','rating':4.4,'is_bestseller':False,'editions':2,'description':'A young thief rises to lead a band of con artists in a Renaissance-inspired fantasy city.'},

        # ── More Sci-Fi ───────────────────────────────────────────────
        {'title':'Snow Crash','author':'Neal Stephenson','genre':'Sci-Fi','year':1992,'isbn':'978-0-553-38095-8','total_copies':2,'cover_color':'#006064','rating':4.2,'is_bestseller':True,'editions':4,'description':'In a future America, a hacker-slash-pizza-deliveryman investigates a dangerous new computer virus.'},
        {'title':'Recursion','author':'Blake Crouch','genre':'Sci-Fi','year':2019,'isbn':'978-1-524-75978-0','total_copies':3,'cover_color':'#1a237e','rating':4.5,'is_bestseller':True,'editions':2,'description':'Memory and reality collide when people begin experiencing someone else life — and dying from it.'},

        # ── More Thriller & Horror ────────────────────────────────────
        {'title':'The Lincoln Lawyer','author':'Michael Connelly','genre':'Thriller','year':2005,'isbn':'978-0-316-73435-8','total_copies':3,'cover_color':'#1b1b2f','rating':4.2,'is_bestseller':True,'editions':3,'description':'A defence attorney who works out of his Lincoln town car takes a case that threatens his life.'},
        {'title':'Bird Box','author':'Josh Malerman','genre':'Horror','year':2014,'isbn':'978-0-062-59024-3','total_copies':3,'cover_color':'#263238','rating':4.1,'is_bestseller':True,'editions':2,'description':'Something is out there and if you see it, you die — a family tries to survive with their eyes covered.'},

        # ── More Business ─────────────────────────────────────────────
        {'title':'Start With Why','author':'Simon Sinek','genre':'Business','year':2009,'isbn':'978-1-591-84280-8','total_copies':3,'cover_color':'#0d47a1','rating':4.3,'is_bestseller':True,'editions':3,'description':'How great leaders inspire action by starting with the question: Why do we do what we do?'},
        {'title':'Thinking in Bets','author':'Annie Duke','genre':'Business','year':2018,'isbn':'978-0-735-21618-2','total_copies':2,'cover_color':'#1b5e20','rating':4.1,'is_bestseller':False,'editions':2,'description':'Making smarter decisions when you do not have all the facts — using lessons from professional poker.'},

        # ── More Psychology ───────────────────────────────────────────
        {'title':'The Paradox of Choice','author':'Barry Schwartz','genre':'Psychology','year':2004,'isbn':'978-0-060-00568-0','total_copies':2,'cover_color':'#4a148c','rating':4.0,'is_bestseller':False,'editions':3,'description':'Why more is less — how the abundance of choice in modern life leads to anxiety and paralysis.'},

        # ── More History ──────────────────────────────────────────────
        {'title':'The Guns of August','author':'Barbara W. Tuchman','genre':'History','year':1962,'isbn':'978-0-345-47609-8','total_copies':2,'cover_color':'#827717','rating':4.4,'is_bestseller':False,'editions':4,'description':'A gripping account of the opening weeks of World War I and the miscalculations that shaped it.'},
        {'title':'Empire of the Summer Moon','author':'S.C. Gwynne','genre':'History','year':2010,'isbn':'978-1-416-59105-6','total_copies':2,'cover_color':'#bf360c','rating':4.5,'is_bestseller':True,'editions':2,'description':'The rise and fall of the Comanche Empire, the most powerful Indian tribe in American history.'},

        # ── Religion & Mythology ──────────────────────────────────────
        {'title':'The Power of Myth','author':'Joseph Campbell','genre':'Religion','year':1988,'isbn':'978-0-385-41886-6','total_copies':2,'cover_color':'#6d4c41','rating':4.5,'is_bestseller':True,'editions':3,'description':'A landmark series of conversations exploring the role of myth in human culture and consciousness.'},
        {'title':'Mythology','author':'Edith Hamilton','genre':'Religion','year':1942,'isbn':'978-0-316-34151-1','total_copies':3,'cover_color':'#880e4f','rating':4.3,'is_bestseller':True,'editions':7,'description':'The timeless collection of Greek, Roman, and Norse myths retold with clarity and elegance.'},

        # ── More Classics ─────────────────────────────────────────────
        {'title':'Wuthering Heights','author':'Emily Bronte','genre':'Classics','year':1847,'isbn':'978-0-141-43955-3','total_copies':3,'cover_color':'#4e342e','rating':4.1,'is_bestseller':True,'editions':9,'description':'The passionate and destructive love between Heathcliff and Catherine on the wild Yorkshire moors.'},
        {'title':'Middlemarch','author':'George Eliot','genre':'Classics','year':1871,'isbn':'978-0-141-43958-7','total_copies':2,'cover_color':'#5d4037','rating':4.2,'is_bestseller':False,'editions':6,'description':'A panoramic portrait of English provincial life following four interlocking story threads.'},

    ]

    added = 0
    for bdata in books:
        if bdata['title'] in existing_titles:
            continue  # skip duplicates for existing databases
        copies = bdata.pop('total_copies')
        b = Book(**bdata, total_copies=copies, avail_copies=copies)
        db.session.add(b)
        added += 1

    members = [
        {'name':'Shivansh Pandey','email':'shivansh.pandey@email.com','phone':'9876543210'},
        {'name':'Shivam Prajapati','email':'shivam.prajapati@email.com','phone':'9123456789'},
        {'name':'Swati Yadav','email':'swati.yadav@email.com','phone':'9988776655'},
        {'name':'Sneha Mehta','email':'sneha.mehta@email.com','phone':'9871234560'},
        {'name':'Arjun Nair','email':'arjun.nair@email.com','phone':'9765432109'},
    ]
    existing_emails = {m.email for m in Member.query.all()}
    for mdata in members:
        if mdata['email'] not in existing_emails:
            db.session.add(Member(**mdata))

    if added > 0:
        db.session.commit()
        print(f"Seeded {added} new books.")


app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)