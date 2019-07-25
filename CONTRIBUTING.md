# Contributing to OpenCue

Code contributions to OpenCue are welcome! Please review this document to get
a briefing on our process.

## Get Connected

The first thing to do, before anything else, is talk to us! Whether you're
reporting an issue, requesting or implementing a feature, or just asking a
question; please don’t hesitate to reach out to project maintainers or the
community as a whole. This is an important first step because your issue,
feature, or the question may have been solved or discussed already, and you’ll
save yourself a lot of time by asking first.

How do you talk to us? There are several ways to get in touch:

* [opencue-dev](https://lists.aswf.io/g/opencue-dev):
This is a development focused mail list.

* [opencue-user](https://lists.aswf.io/g/opencue-user):
This is an end-user oriented mail list.

* [GitHub Issues](https://github.com/AcademySoftwareFoundation/OpenCue/issues):
GitHub **issues** are a great place to start a conversation! Issues aren’t
restricted to bugs; we happily welcome feature requests and other suggestions
submitted as issues. The only conversations we would direct away from issues are
questions in the form of “How do I do X”. Please direct these to the opencue-dev
or opencue-user mail lists, and consider contributing what you've learned to
our docs if appropriate!

## Getting Started

So you’ve broken the ice and chatted with us, and it turns out you’ve found a
gnarly bug that you have a beautiful solution for. Wonderful!

From here on out we’ll be using a significant amount of Git and GitHub based
terminology. If you’re unfamiliar with these tools or their lingo, please look
at the [GitHub Glossary](https://help.github.com/articles/github-glossary/) or
browse [GitHub Help](https://help.github.com/). It can be a bit confusing at
first, but feel free to reach out if you need assistance.

The first requirement for contributing is to have a GitHub account. This is
needed in order to push changes to the upstream repository. After setting up
your account you should then **fork** the OpenCue repository to your
account. This creates a copy of the repository under your user namespace and
serves as the “home base” for your development branches, from which you will
submit **pull requests** to the upstream repository to be merged.

You will also need Git installed on your local development machine. If you need
setup assistance, please see the official
[Git Documentation](https://git-scm.com/doc).

Once your Git environment is operational, the next step is to locally
**clone** your forked OpenCue repository, and add a **remote** pointing to
the upstream OpenCue repository. These topics are covered in
[Cloning a repository](https://help.github.com/articles/cloning-a-repository/)
and
[Configuring a remote for a fork](https://help.github.com/articles/configuring-a-remote-for-a-fork/),
but again, if you need assistance feel free to reach out on the ocio-dev mail
list.

## Contributor License Agreement (CLA) and Intellectual Property

To protect the project -- and the contributors! -- we do require a
Contributor License Agreement (CLA) for anybody submitting changes.

* If you are an individual writing the code on your own time and you're SURE
you are the sole owner of any intellectual property you contribute, you'll
want to sign the Individual CLA.

* If you are writing the code as part of your job, or if there is any
possibility that your employers might think they own any intellectual
property you create, then you should use the Corporate CLA.

Our CLAs are based on those used by Apache and many other open source
projects.

Every pull request runs a check using the Linux Foundation's CLA tool
to verify that all committers have signed the CLA. If you haven't,
the pull request's status check will display the next steps you should
take. You'll log into the CLA tool which will walk you through the
process.

## Development and Pull Requests

Contributions should be submitted as Github pull requests. See
[Creating a pull request](https://help.github.com/articles/creating-a-pull-request/)
if you're unfamiliar with this concept.

The development cycle for a code change should follow this protocol:

1. Create a topic branch in your local repository.

2. Make changes, compile, and test thoroughly. Code style should match existing
style and conventions, and changes should be focused on the topic the pull
request will be addressing. Make unrelated changes in a separate topic branch
with a separate pull request.

3. Push commits to your fork.

4. Create a Github pull request from your topic branch. This can be
a normal pull request or a **draft** pull request:

   -  Normal pull request: Use this if you feel like your change is
   ready to be merged or close to that. Reviews will be automatically
   requested from all of our Code Owners, but feel free to add others
   if you'd like -- we love to get as much feedback as we can!
   
   -  Draft pull request: Use this if you feel like your change isn't
   ready to be merged -- maybe it's just an idea you have -- but
   you want feedback anyway. Reviews will not be automatically
   requested, but feel free to add reviewers anyway and we'll be happy
   to provide feedback -- [CODEOWNERS](./CODEOWNERS) is a good place
   to find a list of potential reviewers.
   
   You can convert a Draft pull request to a regular pull request at any point. 

5. All pull requests (including drafts) trigger our CI system, which builds and
tests your branch. These builds verify that code compiles and all unit tests
succeed. CI build status is displayed on the GitHub pull request page, and
changes will only be merged after all builds have succeeded.

6. Pull requests will be reviewed by project Committers and Contributors,
who may discuss, offer constructive feedback, request changes, or approve
the work.

7. Upon receiving the required number of Committer approvals (as outlined
in [Required Approvals](#required-approvals)), a Committer other than the PR
contributor may squash and merge changes into the master branch.

## Required Approvals

Modifications of the contents of the OpenCue repository are made on a
collaborative basis. Anyone with a GitHub account may propose a modification via
pull request and it will be considered by the project Committers.

Pull requests must meet a minimum number of Committer approvals prior to being
merged. Rather than having a hard rule for all PRs, the requirement is based on
the complexity and risk of the proposed changes, factoring in the length of
time the PR has been open to discussion. The following guidelines outline the
project's established approval rules for merging:

* Core design decisions, large new features, or anything that might be perceived
as changing the overall direction of the project should be discussed at length
in the mail list before any PR is submitted, in order to: solicit feedback, try
to get as much consensus as possible, and alert all the stakeholders to be on
the lookout for the eventual PR when it appears.

* Small changes (bug fixes, docs, tests, cleanups) can be approved and merged by
a single Committer.

* Big changes that can alter behavior, add major features, or present a high
degree of risk should be signed off by TWO Committers, ideally one of whom
should be the "owner" for that section of the codebase (if a specific owner
has been designated). If the person submitting the PR is him/herself the "owner"
of that section of the codebase, then only one additional Committer approval is
sufficient. But in either case, a 48 hour minimum is helpful to give everybody a
chance to see it, unless it's a critical emergency fix (which would probably put
it in the previous "small fix" category, rather than a "big feature").

* Escape valve: big changes can nonetheless be merged by a single Committer if
the PR has been open for over two weeks without any unaddressed objections from
other Committers. At some point, we have to assume that the people who know and
care are monitoring the PRs and that an extended period without objections is
really assent.

Approval must be from Committers who are not authors of the change. If one or
more Committers oppose a proposed change, then the change cannot be accepted
unless:

* Discussions and/or additional changes result in no Committers objecting to the
change. Previously-objecting Committers do not necessarily have to sign-off on
the change, but they should not be opposed to it.

* The change is escalated to the TSC and the TSC votes to approve the change.
This should only happen if disagreements between Committers cannot be resolved
through discussion.

