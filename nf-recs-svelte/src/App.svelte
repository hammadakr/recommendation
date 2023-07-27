<script>
	let name = 'world';
  let member_id_button = null
	let member_id = null
  let hasEntered = false
  const handleButton = (event) => {
    member_id = member_id_button
    userInfo = null
    recommended = null
    hasEntered = true
  }
	const getUserInfo = async (member_id) => {
		if(!member_id){
			return null
		}
		var requestOptions = {
		  method: 'GET',
		  redirect: 'follow'
		};
		let response = await fetch(`http://128.199.22.142/get-user-info/${member_id}`, requestOptions)
		let final = await response.json()
    final['permanent_country'] = 'India'
    final.gallery = final.gallery == 1 ? 'Yes' : 'No'
    final.status = final.status == 1 ? 'Approved' : 'No'
    return final
  }
  let userInfo = null
	$: getUserInfo(member_id).then(value => {userInfo = value}) 

  // const getPastInterests = async (member_id) => {
	// 	if(!member_id){
	// 		return null
	// 	}
	// 	var requestOptions = {
	// 	  method: 'GET',
	// 	  redirect: 'follow'
	// 	};
	// 	let response = await fetch(`http://128.199.22.142/past-interests/${member_id}`, requestOptions)
	// 	let final = await response.json()
  //   final['permanent_country'] = 'India'
  //   final.gallery = final.gallery == 1 ? 'Yes' : 'No'
  //   final.status = final.status == 1 ? 'Approved' : 'No'
  //   return final
  // }
  // let pastInterests = []
	// $: getPastInterests(member_id).then(value => {pastInterests = value}) 
	
  const getRecommendations = async (member_id, userInfo) => {
		if(!member_id || !userInfo){
			return []
		}
    userInfo['gallery'] = userInfo['gallery'].toLowerCase()
    userInfo['gender'] = userInfo['gender'] == 'Male' ? '1' : '2' 

    const helperRenamer = (old_key, new_key) => {
      if (old_key !== new_key) {
    Object.defineProperty(userInfo, new_key,
        Object.getOwnPropertyDescriptor(userInfo, old_key));
    delete userInfo[old_key];
      }
    }

    helperRenamer('status', 'approve_status')
    helperRenamer('gallery', 'gallery_display')
    helperRenamer('highest_education', 'education')
    helperRenamer('sect', 'sub_caste')
    helperRenamer('occupation', 'designation')
    helperRenamer('employed', 'occupation')

    // userInfo['status'] = 'approve_status'
    // userInfo['gallery'] = 'gallery_display'
    // userInfo['highest_education'] = 'education'
    // userInfo['sect'] = 'sub_caste'
    // userInfo['occupation'] = 'designation'
    // userInfo['employed'] = 'occupation'

    console.log('sending: ', userInfo)

    var formdata = new FormData();
    formdata.append("member_id", member_id);
    formdata.append("withInfo", "y");
    formdata.append("offset", "0");
    formdata.append("count", "300");
    formdata.append("userData", JSON.stringify(userInfo));
    formdata.append("timeMix", "0.25");

    var requestOptions = {
      method: 'POST',
      body: formdata,
      redirect: 'follow'
    };
    console.log(JSON.stringify(userInfo))
    let response = await fetch("http://128.199.22.142/recommendation", requestOptions)
    console.log('u')
    let final = await response.json()
    console.log(final)
    return final.userRecommendations
  }
  let recommended = null
  $: getRecommendations(member_id, userInfo).then(value => {
    hasEntered = false
    recommended = value
  })

  const prepareInfoString = (userInfo) => `${userInfo.marital_status} ${userInfo.gender} ${userInfo.caste} employed in ${userInfo.employed} working as ${userInfo.occupation} and from ${userInfo.permanent_city}, ${userInfo.permanent_state} last online: ${(new Date(userInfo.lastonline * 1000)).toDateString()}`

</script>

<div>
  <input type="text" bind:value={member_id_button} on:keypress={(event) => {
    if (event.key === 'Enter')
      handleButton(event)
  }}/>
  <button on:click={handleButton}>Submit</button>
{#if (hasEntered && (recommended == null))}
  <h1>LOADING</h1>
{:else}
<br>
<!-- <select name="flip-1" id="flip-1" data-role="slider">
  <option value="past">Past Interests</option>
  <option value="recommendations">Recommendations</option>
</select>  -->
<h1>Hello {member_id}! You are {userInfo ? prepareInfoString(userInfo) : 'nobody and from nowhere'}</h1>
{#each (recommended ? recommended : []) as rec}
  <h2>{rec.member_id} who is {prepareInfoString(rec)}</h2>
{/each}
{/if}
</div>
