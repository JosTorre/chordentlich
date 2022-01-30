import collections
import random

import aiomas


# A proposal is from a certain "bidder" and has a "value"
Proposal = collections.namedtuple('Proposal', 'bidder, value')


class InitiatorAgent(aiomas.Agent):
    """The initiator sends a *Call for Proposal (CfP)* to all bidders and
    accepts the best proposal."""

    async def run(self, bidder_addrs, target):
        proposals = []
        for addr in bidder_addrs:
            # Connect to the BidderAgent
            bidder_proxy = await self.container.connect(addr)

            # Send a CfP to the agent.
            proposal = await bidder_proxy.cfp(target)
            # The reply is a list, so we need to make a "Proposal" from it:
            proposal = Proposal(*proposal)

            if proposal.value is not None:
                proposals.append(proposal)

        if proposals:
            # Select the proposal that is closest to "target"
            proposal_best = min(proposals, key=lambda p: (target - p.value))

            # Proposal.bidder is a proxy to the respective agent.  We can use
            # it to send a message to it:
            result = await proposal_best.bidder.accept(proposal_best.value)
            proposals.remove(proposal_best)

            for proposal in proposals:
                # The same as before.  "Proposal.bidder" is an agent proxy that
                # we can use to reject the agent:
                await proposal.bidder.reject(proposal.value)

            return result
        return None


class BidderAgent(aiomas.Agent):
    """The BidderAgent answers *Call for Proposal (CfP)* calls.

    Its proposals can be accepted or rejected.

    """

    @aiomas.expose
    def cfp(self, cfp):
        """Reply to a *cfp* with a "Proposal"."""
        print('%s was called for proposal to %s.' % (self, cfp))
        # Randomly choose "None" (no proposal) or a random number:
        value = random.choice([None, random.random()])
        # "self" can be sent to other agents and will be deserialized as
        # a proxy to this agent:
        return Proposal(bidder=self, value=value)

    @aiomas.expose
    def reject(self, reject):
        """Our proposal got rejected :-(."""
        print('%s was rejected for proposal %.2f.' % (self, reject))

    @aiomas.expose
    def accept(self, accept):
        """Our proposal was the best.  Do we accept this outcome?"""
        print('%s was accepted for proposal %.2f.' % (self, accept))
        return random.choice(['nay', 'yay'])

random.seed(0)  # For reproducability

# We first need a container in which all agents will live:
container = aiomas.Container.create(('localhost', 5555))

# Create some agents and pass the container instance to them:
intitiator = InitiatorAgent(container)
bidders = [BidderAgent(container) for _ in range(2)]

# Run the InitiatorAgent with the addresses of the BiddingAgents:
addresses = [b.addr for b in bidders]
result = aiomas.run(intitiator.run(addresses, target=3))
print('The outcome of accepting the bid was "%s".' % result)

# Shutdown the container and close all connections:
container.shutdown()

