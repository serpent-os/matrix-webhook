"""Formatters for matrix webhook."""

import re


def grafana(data, headers):
    """Pretty-print a Grafana (version 8 and older) notification."""
    text = ""
    if "ruleName" not in data and "alerts" in data:
        return grafana_9x(data, headers)
    if "title" in data:
        text = "#### " + data["title"] + "\n"
    if "message" in data:
        text = text + data["message"] + "\n\n"
    if "evalMatches" in data:
        for match in data["evalMatches"]:
            text = text + "* " + match["metric"] + ": " + str(match["value"]) + "\n"
    data["body"] = text
    return data


def grafana_9x(data, headers):
    """Pretty-print a Grafana newer than v9.x notification."""
    text = ""
    if "title" in data:
        text = "#### " + data["title"] + "\n"
    if "message" in data:
        text = text + data["message"].replace("\n", "\n\n") + "\n\n"
    data["body"] = text
    return data


def github(data, headers):
    """Pretty-print a github notification."""
    # TODO: Write nice useful formatters. This is only an example.
    repository = data['repository']
    if repository['private'] and repository['visibility'] == "private":
        pass
        # GH webhook will get a 400 return code w/missing body
    elif headers['X-GitHub-Event'] == "push":
        pusher, ref, a, b, c = (
            data[k] for k in ["pusher", "ref", "after", "before", "compare"]
        )
        pusher_url = f"[@{pusher['name']}](https://github.com/{pusher['name']})"
        # Since we use monorepos and use an org-wide webhook, let's add repo info too.
        repo_url = f"[{repository['full_name']}]({repository['html_url']})"

        if len(data['commits']) == 0:
            # The user deleted a branch
            data['body'] = f"{repo_url}: {pusher_url} deleted branch _{ref}_.\n"
        else:
            # The commit shasum hashes are noisy, so just make the ref link to the full compare
            data['body'] = f"{repo_url}: {pusher_url} pushed on [{ref}]({c}):\n\n"

        commits = 0
        for commit in data['commits']:
            # Elide commit list once we go past a reasonable number of commits for readability
            if commits >= 5:
                data['body'] += f"- (...)\n"
                break
            # We only really need the shortlog of each relevant commit
            shortlog = commit['message'].strip().split("\n")[0]
            data['body'] += f"- [{shortlog}]({commit['url']})\n"
            commits += 1
    elif headers['X-GitHub-Event'] == "pull_request":
        action, number, pr = (
            data[k] for k in ["action", "number", "pull_request"]
        )
        # avoid PR spam and wasted CPU cycles
        if action in ["opened", "closed", "reopened", "edited",
                      "ready for review", "review requested"]:
            pr_title = pr['title']
            pr_url = pr['html_url']
            pr_user = pr['user']['login']
            reponame = repository['full_name']
            repo_url = repository['html_url']
            url_query = "pulls/"

            if action == "closed":
                url_query="pulls/?q=is%3Apr+is%3Aclosed"

            data['body'] = f"PR#{number} [{pr_title}]({pr_url})\n\n"
            data['body'] += f"{action} by [@{pr_user}](https://github.com/{pr_user}) "
            data['body'] += f"in [{reponame}]({repo_url}/{url_query})"
        # endif
        # GH webhook will get a 400 return code w/missing body if the action
        # isn't in the allow-list
    else:
        event = headers['X-GitHub-Event']
        data['body'] = f"unsupported github event: '{event}'"
    data['digest'] = headers['X-Hub-Signature-256'].replace("sha256=", "")
    return data


def gitlab_gchat(data, headers):
    """Pretty-print a gitlab notification preformatted for Google Chat."""
    data["body"] = re.sub("<(.*?)\\|(.*?)>", "[\\2](\\1)", data["body"], re.MULTILINE)
    return data


def gitlab_teams(data, headers):
    """Pretty-print a gitlab notification preformatted for Microsoft Teams."""
    body = []
    for section in data["sections"]:
        if "text" in section.keys():
            text = section["text"].split("\n\n")
            text = ["* " + t for t in text]
            body.append("\n" + "  \n".join(text))
        elif all(
            k in section.keys()
            for k in ("activityTitle", "activitySubtitle", "activityText")
        ):
            text = section["activityTitle"] + " " + section["activitySubtitle"] + " → "
            text += section["activityText"]
            body.append(text)

    data["body"] = "  \n".join(body)
    return data
