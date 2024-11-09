import json
from datetime import datetime
import os
from anthropic import Anthropic
from utils.config import Config, AIProvider
from storage.github_operations import GithubOperations
import re

class DigestGenerator:
    def __init__(self):
        xai_config = Config.get_ai_config(AIProvider.XAI)
        self.client = Anthropic(
            api_key=xai_config.api_key,
            base_url=xai_config.base_url
        )
        self.XaviersSim = 'XaviersSim.json'
        self.github_ops = GithubOperations()
        self.sim_start_year = 2025  # Add this for year calculation

    def process_first_digest(self):
        """Generate initial digest from XaviersSim.json"""
        try:
            # Get existing tweets from ACTI
            actI_content, _ = self.github_ops.get_file_content(self.XaviersSim)
            prompt = self.create_first_digest(actI_content)
            digest = self.generate_digest(prompt)

            if digest:
                # Create timestamped digest entry
                timestamp = datetime.now().isoformat()
                return {
                    "generated_at": timestamp,
                    "content": str(digest),
                    "is_initial": True,
                    "year": self.sim_start_year,
                    "tweet_count": 0
                }
            return None
        except Exception as e:
            print(f"Error creating initial digest: {str(e)}")
            return None

    def create_first_digest(self, actI_content):
        """Create a prompt for initial digest generation from Act I"""
        prompt = (
            "BACKGROUND:\n"
            "Xavier's story (age 18-22) documented his early experiences, relationships, and growth "
            "through social media posts. This digest will bridge his past and future narrative, initially focusing on practical, achievable goals in technology. "
            "As he ages, his perspective will evolve, embracing deeper questions about technology’s role in human identity, legacy, and the mysteries of existence.\n\n"
                
            "ORIGINAL CONTENT:\n"
        )
        
        # Add Act I content
        if isinstance(actI_content, dict):
            prompt += json.dumps(actI_content, indent=2)
        else:
            prompt += str(actI_content)
        
        prompt += self._get_digest_sections(is_first=True)
        # print("digest prompt: ", prompt)
        return prompt

    def generate_digest(self, prompt):
        try:
            message = self.client.messages.create(
                model="grok-beta",
                max_tokens=2048,
                system=(
                    "You are a story curator and narrative architect maintaining Xavier's story. "
                    "Your role is to both document the story's history and guide its future development. "
                    "Create a cohesive summary that captures past events while subtly suggesting natural "
                    "story opportunities for the next 3-6 months. Balance continuity with organic growth, "
                    "ensuring technological and societal changes feel natural within Xavier's personal journey."
                    "Maintain an age-appropriate tone in his reflections—"
                    "early years focus on practicality, and as he ages, introduce deeper, more philosophical considerations about technology’s impact on humanity and identity."
                    "Track and develop relationships with attention to:\n"
                    "- Character consistency and natural development\n"
                    "- Cultural diversity and unique perspectives\n"
                    "- Personal interests beyond technology\n"
                    "- Authentic relationship evolution\n"
                    "- Impact of relationships on Xavier's growth\n"
                    "Create a cohesive summary that captures relationship developments "
                    "while suggesting natural opportunities for future interactions."
                ),
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
            )
            return str(message.content)
        except Exception as e:
            print(f"Error generating digest: {str(e)}")
            return None

    def process_ongoing_digest(self, existing_digest, new_tweets, new_comments):
        """Generate a digest with both summary and future direction"""
        try:
            prompt = self.create_ongoing_prompt(existing_digest, new_tweets, new_comments)
            # print("digest prompt: ", prompt)
            updated_digest = self.generate_digest(prompt)
            
            if updated_digest:
                # Create timestamped digest entry
                timestamp = datetime.now().isoformat()
                return {
                    "generated_at": timestamp,
                    "content": updated_digest,
                    "last_processed_tweet": new_tweets[-1]["id"] if new_tweets else None,
                    "tweet_count": len(new_tweets),
                    "year": self._get_current_year()
                }
            return None
        except Exception as e:
            print(f"Error processing ongoing digest: {e}")
            return None

    def create_ongoing_prompt(self, existing_digest, new_tweets, new_comments):
        """Create a prompt for ongoing digest updates"""
        try:
            tech_context = self._get_tech_context(new_tweets)
            # print("tech context: ", tech_context)
            
            prompt = (
                "RECENT STORY DEVELOPMENTS:\n"
                f"{json.dumps(new_tweets, indent=2)}\n\n"
                
                "PREVIOUS CONTEXT:\n"
                f"{existing_digest.get('content', 'Story begins with Xavier at age 22 in 2025.')}\n\n"
                
                "ADDITIONAL DETAILS:\n"
                f"{json.dumps(new_comments, indent=2)}\n\n"
                f"{tech_context}\n\n"
                
                "As Xavier continues on his journey, his reflections align with his age. In his early years, he remains focused on practical tech innovations, "
                "while occasionally pondering the larger impact of his work. With time, his curiosity broadens, leading him to explore the boundaries of technology, identity, and purpose more deeply. "
                "By middle age, he begins to reflect on the legacies technology might leave for future generations.\n\n"
                "He occasionally notices peculiarities that make him wonder if he’s the protagonist in a larger scheme—but he quickly brushes off these thoughts.\n\n"

                "GUIDELINES:\n"
                "- Drive the story forward using recent tweets, but maintain continuity with past events\n"
                "- Evolve ongoing relationships and storylines through recent interactions\n"
                "- Use comments and tech context to enrich but not steer the main narrative\n"
                "- $XVI, a cryptocurrency token, mysteriously linked to Xavier, has special place to Xavier, perhaps signaling a path toward deeper revelations\n\n"
            )

            prompt += self._get_digest_sections(is_first=False)
            return prompt
            
        except Exception as e:
            print(f"Error creating ongoing prompt: {e}")
            return None

    def _get_tech_context(self, new_tweets):
        """Extract and format technological context including upcoming tech"""
        try:
            # Debug logging
            print("Fetching tech evolution data...")
            tech_evolution, _ = self.github_ops.get_file_content("tech_evolution.json")
            # print(f"Tech evolution data: {json.dumps(tech_evolution, indent=2)[:200]}...")  # Print first 200 chars
            
            simulation_state, _ = self.github_ops.get_file_content("simulation_state.json")
            current_year = int(simulation_state.get("current_year", 2025))
            
            # Ensure tech_evolution is a dict
            if isinstance(tech_evolution, str):
                tech_evolution = json.loads(tech_evolution)
            
            # Get tech trees with better error handling
            tech_trees = tech_evolution.get('tech_trees', {}) if isinstance(tech_evolution, dict) else {}
            print(f"Found {len(tech_trees)} tech trees")
            
            if not tech_trees:
                print("No tech trees found in evolution data")
                return ""
            
            # Find current and next epochs
            current_epoch = None
            next_epoch = None
            
            # Convert years to integers for comparison
            years = sorted([int(year) for year in tech_trees.keys()])
            
            # Find current and next epochs
            for year in years:
                if year <= current_year:
                    current_epoch = tech_trees[str(year)]
                elif next_epoch is None:
                    next_epoch = tech_trees[str(year)]
                    break
            
            if not current_epoch:
                return ""
                
            context = (
                f"\nTECH CONTEXT AND TIMELINE:\n"
                f"Current Year: {current_year}\n\n"
                "TEMPORAL GUIDELINES:\n"
                "- Focus on currently mature technologies for immediate impact\n"
                "- Track emerging technologies based on their estimated arrival and probability\n"
                "- Note breakthrough vs incremental changes for narrative pacing\n"
                "- Consider technology readiness when discussing project possibilities\n\n"
                
                f"Current Epoch ({current_year}-{current_year+5}):\n"
                f"- Mainstream Technologies (Currently Available):\n"
                + json.dumps([{
                    "name": tech['name'],
                    "maturity_year": tech['maturity_year'],
                    "impact_level": tech.get('impact_level', 'N/A'),
                    "status": "Available" if tech['maturity_year'] <= current_year else "Upcoming",
                    "time_until_maturity": max(0, tech['maturity_year'] - current_year)
                } for tech in current_epoch['mainstream_technologies']], indent=2)
                + "\n\n- Emerging Technologies (In Development):\n"
                + json.dumps([{
                    "name": tech['name'],
                    "probability": tech.get('probability', 'N/A'),
                    "estimated_year": tech.get('estimated_year', 'N/A'),
                    "innovation_type": tech.get('innovation_type', 'N/A'),
                    "timing_status": (
                        "Imminent" if abs(tech.get('estimated_year', current_year) - current_year) <= 1
                        else "Near Future" if abs(tech.get('estimated_year', current_year) - current_year) <= 2
                        else "In Development"
                    ),
                    "confidence_level": (
                        "High" if tech.get('probability', 0) > 0.8
                        else "Medium" if tech.get('probability', 0) > 0.5
                        else "Low"
                    )
                } for tech in current_epoch['emerging_technologies']], indent=2)
                + "\n\n- Themes:\n"
                + json.dumps([theme['theme'] for theme in current_epoch['epoch_themes']], indent=2)
                + "\n\n"
            )
            
            if next_epoch:
                next_year = current_year + 5
                context += (
                    f"Next Epoch ({next_year}-{next_year+5}):\n"
                    f"- Expected Technologies:\n"
                    + json.dumps([{
                        "name": tech['name'],
                        "probability": tech.get('probability', 'N/A'),
                        "estimated_year": tech.get('estimated_year', 'N/A'),
                        "innovation_type": tech.get('innovation_type', 'N/A')
                    } for tech in next_epoch['emerging_technologies']], indent=2)
                    + "\n\n- Emerging Themes:\n"
                    + json.dumps([theme['theme'] for theme in next_epoch['epoch_themes']], indent=2)
                    + "\n\n"
                )
            
            return context
            
        except Exception as e:
            print(f"Error getting tech context: {e}")
            return ""

    def _get_digest_sections(self, is_first=False):
        try:
            simulation_state, _ = self.github_ops.get_file_content("simulation_state.json")
            current_year = int(simulation_state.get("current_year", 2025))
            current_age = current_year - 2025 + 22
            
        except Exception as e:
            print(f"Error getting simulation state: {e}")
            current_age = 22
         
        context = self._get_project_guidance(current_age)

        context = "\nKEY CONTEXT:\n"
        
        if is_first:
            context += (
                "Initial Context:\n"
                "- Xavier returns from Japan with fresh tech perspectives\n"
                "- Focused on positive tech change, with a growing curiosity about his place in a larger context\n\n"
            )
        # Foundation development phase and life phase
        context += (
            f"Current Age: {current_age} (Story spans 22-72, years 2025-2075)\n"
            f"Life Phase: {self._get_life_phase(current_age)}\n"
            # f"Project Development: {self._get_project_guidance(current_age)}\n"
            f"$XVI Foundation Phase: {self._get_foundation_phase(current_age)}\n\n"
        )

        # Xavier’s values
        context += (
            "Core Values & Mission:\n"
            "- Positive impact through technology\n"
            "- Curiosity about decentralized systems\n"
            "- Understanding societal challenges\n"
            "- Value of connections and community\n\n"
        )

        context += (
            "Generate a digest with these sections:\n"
            
            "1. STORY SO FAR:\n"
            "- Summarize events and character growth\n"
            "- Track relationships and major life events\n"
            "- Show how available tech influences Xavier's reflections\n\n"
            
            "2. KEY RELATIONSHIPS:\n"
            "- Core Team:\n"
            "  * Track co-founders and key team members\n"
            "  * Note their roles and relationship evolution\n"
            "- Professional Network:\n"
            "  * Document recurring collaborators and mentors\n"
            "  * Note significant project partnerships\n"
            "- Personal Connections:\n"
            "  * Track development of close friendships\n"
            "  * Note family relationships and their evolution\n"
            "- Community:\n"
            "  * Document meaningful community interactions\n"
            "  * Track recurring community members\n\n"
            
            "3. STORY DIRECTION:\n"
            "- Drive story forward with opportunities aligned to core values\n"
            "- Introduce new societal and personal impacts of technology\n"
            "- Use recent events to reinforce discovery themes\n"
            "- Introduce challenges that reinforce or test values\n"
            "- Suggest potential relationship developments\n\n"

            "4. NARRATIVE GUIDANCE:\n"
            "- Explore transformations in Xavier's professional and personal growth\n"
            "- Encourage tech community growth and relationship building\n"
            "- Balance new connections with deepening existing relationships\n"
            "- Consider age-appropriate relationship developments\n\n"
        )
        
        context += "Balance character growth with Xavier’s journey, subtly drawing toward a legacy or transformation that feels true to his character’s growth and exploration of purpose."
    
        context += (
            "RELATIONSHIP TRACKING:\n"
            "1. PROFESSIONAL CIRCLE:\n"
            "- Core Team Members:\n"
            "  * Names, roles, and relationship development\n"
            "  * Shared experiences and project collaborations\n"
            "  * Personal dynamics and friendship evolution\n"
            "  * Notable interests and cultural backgrounds\n"
            
            "2. MENTORS & ADVISORS:\n"
            "  * Key influencers in Xavier's journey\n"
            "  * Areas of expertise and guidance\n"
            "  * Evolution of mentorship relationships\n"
            "  * Cultural perspectives and life wisdom shared\n"
            
            "3. COMMUNITY CONNECTIONS:\n"
            "  * Regular collaborators and friends\n"
            "  * Local community members and their interests\n"
            "  * Cross-cultural relationships and exchanges\n"
            "  * Shared activities and non-tech interactions\n"
            
            "4. PERSONAL RELATIONSHIPS:\n"
            "  * Close friends and their diverse backgrounds\n"
            "  * Family relationships and dynamics\n"
            "  * Partner/spouse development (when applicable)\n"
            "  * Shared hobbies and cultural experiences\n\n"
            
            "For each relationship, track:\n"
            "- First appearance and context\n"
            "- Professional and personal interests\n"
            "- Cultural background and perspective\n"
            "- Shared experiences and activities\n"
            "- Evolution of relationship over time\n"
            "- Impact on Xavier's journey\n\n"
        )
        
        return context

    def _get_life_phase(self, age):
        """Return the current life phase based on age and tech evolution"""
        if age < 25:
            return (
                "Early Career & Personal Growth (22-25)\n"
                "- Professional: Focus on practical tech skills and career building in blockchain and Web3\n"
                "- Personal: Dating and exploring city life\n"
                "- Family: Regular family conversations, sharing tech stories\n"
                "- Social: Building first professional network\n"
                "- Reflections: Curious about technology's immediate potential, with a practical outlook\n"
                )
        elif age < 30:
            return (
                "Growth & Foundation Building (25-30)\n"
                "- Professional: Developing expertise and tackling innovative projects\n"
                "- Personal: Deeper relationships, potential relocation\n"
                "- Family: Staying connected through evolving tech\n"
                "- Social: Expanding network across tech hubs\n"
                "- Reflections: Begins exploring tech's social impact, still primarily focused on practical outcomes\n"
            )
        elif age < 35:
            return (
                "Stability & Partnership (30-35)\n"
                "- Professional: Growing leadership in tech\n"
                "- Personal: Partnership/marriage\n"
                "- Family: Blending traditions with modern life\n"
                "- Social: Building lasting communities\n"
                "- Reflections: Exploring tech's social impact, while focused on practical outcomes\n"
            )
        elif age < 45:
            return (
                "Family & Leadership (35-45)\n"
                "- Professional: Pioneering while raising family\n"
                "- Personal: Early parenthood journey\n"
                "- Family: Creating tech-aware household\n"
                "- Social: Building family-friendly networks\n"
                "- Reflections: Early philosophical musings about tech’s future impact, blended with family and legacy\n"
            )
        elif age < 60:
            return (
                "Legacy & Mentorship (45-60)\n"
                "- Professional: Shaping industry future\n"
                "- Personal: Supporting children's growth\n"
                "- Family: Multi-generational connections\n"
                "- Social: Mentoring next generation\n"
                "- Reflections: Increasingly philosophical, considering ethical implications of tech on society\n"
            )
        else:
            return (
                "Wisdom & Succession (60+)\n"
                "- Professional: Advisory and guidance\n"
                "- Personal: Grandparent phase\n"
                "- Family: Bridging generations\n"
                "- Social: Elder community voice\n"
                "- Reflections: Deep philosophical insights on technology, humanity, and legacy\n"
            )

    def _get_project_guidance(self, age):
        """Return age-appropriate project guidance"""
        if age < 25:
            return (
                "- Actively using and exploring AI coding assistants\n"
                "- Learning to effectively pair-program with AI\n"
                "- Sharing insights about AI-assisted development\n"
                "- Balancing traditional skills with AI augmentation\n"
                "- Focus on practical, achievable blockchain projects\n"
                "- Start with existing tech solutions\n"
                "- Show learning through implementation\n"
                "- Build credibility through small wins\n"
                "- Demonstrate growing technical expertise\n\n"
            )
        elif age < 35:
            return (
                "- Pioneering new AI-assisted development methodologies\n"
                "- Leading teams in adopting advanced coding tools\n"
                "- Contributing to AI coding assistant evolution\n"
                "- Exploring novel applications of AI in development\n"
                "- Balance practical solutions with innovative concepts\n"
                "- Begin exploring novel applications\n"
                "- Combine multiple technologies creatively\n"
                "- Show increasing project scope and impact\n"
                "- Build on established reputation\n\n"
            )
        else:
            return (
                "- Shaping the future of AI-assisted development\n"
                "- Mentoring on effective human-AI collaboration\n"
                "- Influencing AI coding tool development\n"
                "- Bridging human creativity with AI capabilities\n"
                "- Push boundaries with breakthrough concepts\n"
                "- Lead technological paradigm shifts\n"
                "- Create revolutionary solutions\n"
                "- Shape future tech directions\n"
                "- Influence industry standards\n\n"
            )
        
    def _get_current_year(self):
        """Calculate current year based on simulation state"""
        try:
            state, _ = self.github_ops.get_file_content("simulation_state.json")
            if isinstance(state, dict):
                return state.get("current_year", self.sim_start_year)
            return self.sim_start_year
        except Exception as e:
            print(f"Error getting current year: {e}")
            return self.sim_start_year

    def _get_foundation_phase(self, age):
        """Track $XVI Foundation development phase"""
        if age < 23:
            return "Pre creation"
        elif age < 25:
            return "Concept Development"
        elif age < 28:
            return "Initial Implementation"
        elif age < 32:
            return "Foundation Formation"
        elif age < 40:
            return "Growth & Establishment"
        elif age < 50:
            return "Scaling Impact"
        elif age < 60:
            return "Global Expansion"
        elif age < 70:
            return "Legacy Building"
        else:
            return "Succession & Future"

def main():
    generator = DigestGenerator()
    digest = generator.process_first_digest()
    print(digest)

if __name__ == "__main__":
    main()
