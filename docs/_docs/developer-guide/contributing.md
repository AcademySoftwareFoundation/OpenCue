---
title: "Contributing to OpenCue"
linkTitle: "Contributing to OpenCue"
parent: "Developer Guide"
nav_order: 56
layout: default
date: 2020-05-04
description: >
  Contribute to OpenCue development
---

# Contributing to OpenCue

Welcome! We're excited that you're interested in contributing to OpenCue. This guide will help you get started with your first contribution.

## Quick Start

### 1. Connect with the Community First

Before diving into code, connect with us! This helps avoid duplicate work and ensures your contribution aligns with the project's direction.

**Where to connect:**
- **[Slack Channel](https://academysoftwarefdn.slack.com/archives/CMFPXV39Q)** - Best for quick questions and discussions
- **[GitHub Issues](https://github.com/AcademySoftwareFoundation/OpenCue/issues)** - For bug reports, feature requests, and tracking work
- **[Mailing Lists](https://lists.aswf.io/g/opencue-dev)** - For broader discussions and "how-to" questions

### 2. Set Up Your Development Environment

#### Prerequisites
- GitHub account
- Git installed locally
- Basic familiarity with Git workflows

#### Setup Steps

1. **Fork the repository**
   - Visit [OpenCue on GitHub](https://github.com/AcademySoftwareFoundation/OpenCue)
   - Click "Fork" to create your own copy

2. **Clone your fork locally**
   ```bash
   git clone https://github.com/YOUR_USERNAME/OpenCue.git
   cd OpenCue
   ```

3. **Add upstream remote**
   ```bash
   git remote add upstream https://github.com/AcademySoftwareFoundation/OpenCue.git
   ```

4. **Set up the development environment**
   - Follow the [sandbox testing guide](/docs/developer-guide/sandbox-testing/)
   - This provides a local OpenCue instance for testing

## Before You Code

### Find or Create an Issue

Every contribution should have an associated GitHub issue. This helps us:
- Avoid duplicate work
- Track related discussions
- Generate accurate release notes

**Working with issues:**
1. Search [existing issues](https://github.com/AcademySoftwareFoundation/OpenCue/issues) first
2. If none exists, create a new one describing your planned work
3. Wait for feedback before starting major changes
4. Look for "good first issue" labels if you're new

### Understanding the Codebase

- Review the [repository structure](https://github.com/AcademySoftwareFoundation/OpenCue/blob/master/README.md)
- Check existing code style and conventions
- Run existing tests to understand the testing approach

## Making Your Contribution

### Development Workflow

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write clean, well-documented code
   - Follow existing code style
   - Keep changes focused on a single issue

3. **Test thoroughly**
   - Run all existing tests
   - Add tests for new functionality
   - Test in the sandbox environment

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "Clear, descriptive commit message"
   ```

5. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

### Creating a Pull Request

#### Choose the Right Type

- **Regular Pull Request**: Your code is ready for review and merging
- **Draft Pull Request**: You want early feedback on work in progress

#### Pull Request Process

1. **Create the PR** from your fork to the main OpenCue repository
2. **Fill out the template** completely
3. **Link the related issue** using keywords like "Fixes #123"
4. **Wait for CI checks** to complete
5. **Address review feedback** promptly
6. **Keep your branch updated** with the main branch

### What Happens Next?

- Automated CI runs tests and checks
- Code owners are automatically assigned for review
- Community members provide feedback
- Once approved, a committer will merge your changes

## Contributor License Agreement (CLA)

We require a CLA to protect both the project and contributors.

**Which CLA to sign:**
- **Individual CLA**: If you own the intellectual property of your contribution
- **Corporate CLA**: If your employer might claim ownership of your work

The CLA check runs automatically on your first pull request. Follow the prompts to complete the process.

## Best Practices

### Do's
- Communicate early and often
- Keep pull requests focused and small
- Write clear commit messages
- Add tests for new features
- Update documentation
- Be patient and respectful

### Don'ts
- Submit large, unfocused changes
- Skip tests or documentation
- Ignore CI failures
- Be discouraged by feedback

## Getting Help

Stuck? Need help? We're here for you!

- Ask in [Slack](https://academysoftwarefdn.slack.com/archives/CMFPXV39Q)
- Comment on your issue or PR
- Check our [documentation](https://docs.opencue.io)
- Review [GitHub Help](https://help.github.com/)

## Thank You!

Your contributions make OpenCue better for everyone. We appreciate your time and effort in improving the project!

---

*Remember: Every expert was once a beginner. Don't hesitate to ask questions and learn from the community.*