# peer-review
Matches people to peer review assignments in Minerva

The code should be scheduled to run on crontab or similar. It takes results from the typeform api of people who submitted requests to have their works peer reviewed, then inserts the new submissions into a mysql database. An algorithm then attempts to match people who submitted requests to people who have the same assignment and similar grades to them. If a match is made, an email is sent to the matched people to inform them.
